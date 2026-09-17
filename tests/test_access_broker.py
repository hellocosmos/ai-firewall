"""Strict inline authorization and side-effect-free mirror evaluation."""

from __future__ import annotations

import hashlib
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import timedelta

import pytest

from asr_proxy.access_broker import (
  AccessBroker,
  AccessRequest,
  AgentRecord,
  ApprovalDecisionRequest,
  DelegationCreateRequest,
  FileAccessBrokerStore,
)
from asr_proxy.access_broker.models import utc_now


def _setup(store=None, *, action="read"):
  broker = AccessBroker(store)
  broker.register_agent(AgentRecord(
    agent_id="agent-a", tenant_id="tenant-a", owner_id="owner-a",
    allowed_tools=["documents.read", "documents.deploy"],
    allowed_resources=["document:one"],
  ))
  broker.create_delegation(DelegationCreateRequest(
    delegation_id="delegation-a", tenant_id="tenant-a", user_id="user-a",
    agent_id="agent-a", task_id="task-a", purpose="Synthetic authorization test",
    allowed_resources=["document:one"], allowed_actions=["read", "deploy"],
  ))
  request = AccessRequest(
    tenant_id="tenant-a", user_id="user-a", agent_id="agent-a",
    agent_instance_id="instance-a", delegation_id="delegation-a", task_id="task-a",
    tool_name=f"documents.{action}", resource_id="document:one", requested_action=action,
    metadata={"request_digest": hashlib.sha256(b"synthetic final request").hexdigest()},
  )
  return broker, request


def _snapshot(store):
  return {
    "agents": [item.model_dump(mode="json") for item in store.list_agents()],
    "delegations": [item.model_dump(mode="json") for item in store.list_delegations()],
    "approvals": [item.model_dump(mode="json") for item in store.list_approvals()],
    "audit": [item.model_dump(mode="json") for item in store.list_audit_events(10_000)],
  }


def _approved(broker, request):
  decision = broker.authorize(request)
  assert decision.action == "approval_required"
  assert decision.token is None
  assert decision.approval.request_digest == request.metadata["request_digest"]
  broker.approve(decision.approval.approval_id, ApprovalDecisionRequest(approver_id="operator-a"))
  return request.model_copy(update={"approval_id": decision.approval.approval_id})


@pytest.mark.parametrize("action, expected", [("read", "allow"), ("deploy", "approval_required")])
def test_mirror_evaluation_does_not_mutate_any_broker_state(action, expected):
  broker, request = _setup(action=action)
  before = _snapshot(broker.store)
  for _ in range(3):
    decision = broker.evaluate(request)
    assert decision.action == expected
    assert decision.token is None
    assert decision.approval is None
    assert decision.metadata["evaluation_only"] is True
    assert decision.metadata["enforcementApplied"] is False
  assert _snapshot(broker.store) == before


def test_mirror_denial_does_not_write_audit():
  broker, request = _setup()
  before = _snapshot(broker.store)
  decision = broker.evaluate(request.model_copy(update={"agent_id": "unknown"}))
  assert decision.action == "block"
  assert _snapshot(broker.store) == before


def test_file_mirror_reads_current_snapshot_without_writing(tmp_path):
  path = tmp_path / "broker.json"
  broker, request = _setup(FileAccessBrokerStore(path), action="deploy")
  mirror = AccessBroker(FileAccessBrokerStore(path))
  request = _approved(broker, request)
  before = path.read_bytes()
  before_stat = path.stat().st_mtime_ns
  decision = mirror.evaluate(request)
  assert decision.action == "allow"
  assert decision.token is None and decision.approval is None
  assert path.read_bytes() == before
  assert path.stat().st_mtime_ns == before_stat
  assert mirror.store.get_approval(request.approval_id).consumed_at is None


def test_evaluating_empty_file_store_creates_no_files(tmp_path):
  path = tmp_path / "uncreated" / "broker.json"
  _, request = _setup()
  decision = AccessBroker(FileAccessBrokerStore(path)).evaluate(request)
  assert decision.reason_code == "agent_not_registered"
  assert not path.parent.exists()


def test_inline_read_issues_bound_evidence_and_audit():
  broker, request = _setup()
  decision = broker.authorize(request)
  assert decision.action == "allow"
  assert decision.token.tenant_id == request.tenant_id
  assert decision.token.request_digest == request.metadata["request_digest"]
  assert decision.token.scopes == ["document:one:read"]
  assert decision.metadata["evaluation_only"] is False
  assert decision.metadata["enforcementApplied"] is False
  assert broker.store.list_audit_events()[-1].event_type == "access.decision"


def test_management_mutation_actor_is_optional_and_audited():
  broker = AccessBroker()
  agent = AgentRecord(agent_id="actor-agent", tenant_id="tenant-a", owner_id="owner-a")
  broker.register_agent(agent)
  assert "actor" not in broker.store.list_audit_events()[-1].payload
  broker.register_agent(agent, actor={
    "principal_id": "ops-admin", "tenant_id": "tenant-a", "authentication": "oidc",
  })
  assert broker.store.list_audit_events()[-1].payload["actor"] == {
    "principal_id": "ops-admin", "tenant_id": "tenant-a", "authentication": "oidc",
  }


def test_approved_inline_request_succeeds_once_and_mirror_never_consumes():
  broker, request = _setup(action="deploy")
  request = _approved(broker, request)
  before = _snapshot(broker.store)
  for _ in range(2):
    assert broker.evaluate(request).action == "allow"
  assert _snapshot(broker.store) == before
  assert broker.authorize(request).action == "allow"
  replay = broker.authorize(request)
  assert replay.action == "block"
  assert replay.reason_code == "approval_consumed"
  assert replay.token is None
  assert broker.evaluate(request).reason_code == "approval_consumed"
  with pytest.raises(ValueError, match="already decided or consumed"):
    broker.approve(request.approval_id, ApprovalDecisionRequest(approver_id="operator-a"))


@pytest.mark.parametrize("field, value", [
  ("tenant_id", "tenant-b"), ("user_id", "user-b"), ("task_id", "task-b"),
  ("agent_instance_id", "instance-b"),
  ("metadata", {"request_digest": hashlib.sha256(b"different request").hexdigest()}),
])
def test_approval_is_bound_to_tenant_identity_task_and_final_request(field, value):
  broker, request = _setup(action="deploy")
  request = _approved(broker, request)
  decision = broker.authorize(request.model_copy(update={field: value}))
  assert decision.action == "block"
  assert broker.store.get_approval(request.approval_id).consumed_at is None
  assert broker.authorize(request).action == "allow"


@pytest.mark.parametrize("field", ["allowed_tools", "allowed_resources"])
def test_empty_agent_scope_is_deny_all(field):
  broker, request = _setup()
  agent = broker.store.get_agent(request.agent_id).model_copy(update={field: []})
  broker.store.upsert_agent(agent)
  assert broker.evaluate(request).action == "block"


@pytest.mark.parametrize("field", ["allowed_actions", "allowed_resources"])
def test_empty_delegation_scope_is_deny_all(field):
  broker, request = _setup()
  delegation = broker.store.get_delegation(request.delegation_id).model_copy(update={field: []})
  broker.store.create_delegation(delegation)
  assert broker.evaluate(request).action == "block"


@pytest.mark.parametrize("change, reason", [
  ({"tenant_id": None}, "tenant_required"),
  ({"metadata": {}}, "request_digest_required"),
  ({"metadata": {"request_digest": "invalid"}}, "request_digest_required"),
])
def test_strict_context_is_required(change, reason):
  broker, request = _setup()
  assert broker.evaluate(request.model_copy(update=change)).reason_code == reason


@pytest.mark.parametrize("record_type, tenant", [("agent", None), ("delegation", None), ("delegation", "tenant-b")])
def test_unbound_or_cross_tenant_records_are_denied(record_type, tenant):
  broker, request = _setup()
  if record_type == "agent":
    record = broker.store.get_agent(request.agent_id).model_copy(update={"tenant_id": tenant})
    broker.store.upsert_agent(record)
  else:
    record = broker.store.get_delegation(request.delegation_id).model_copy(update={"tenant_id": tenant})
    broker.store.create_delegation(record)
  assert broker.evaluate(request).reason_code == f"{record_type}_tenant_mismatch"


def test_pending_approval_is_reused_and_denial_is_terminal():
  broker, request = _setup(action="deploy")
  pending = broker.authorize(request).approval
  request = request.model_copy(update={"approval_id": pending.approval_id})
  assert broker.authorize(request).approval.approval_id == pending.approval_id
  assert len(broker.store.list_approvals()) == 1
  broker.deny(pending.approval_id, ApprovalDecisionRequest(approver_id="operator-a"))
  assert broker.evaluate(request).reason_code == "approval_denied"
  with pytest.raises(ValueError):
    broker.approve(pending.approval_id, ApprovalDecisionRequest(approver_id="operator-a"))


def test_unknown_approval_blocks_without_creating_another():
  broker, request = _setup(action="deploy")
  decision = broker.authorize(request.model_copy(update={"approval_id": "unknown"}))
  assert decision.reason_code == "approval_not_found"
  assert broker.store.list_approvals() == []


def test_approval_expiry_is_checked_on_approve_and_authorize():
  broker, request = _setup(action="deploy")
  approval = broker.authorize(request).approval
  assert approval.expires_at <= broker.store.get_delegation(request.delegation_id).expires_at
  expired = approval.model_copy(update={"expires_at": utc_now() - timedelta(seconds=1)})
  broker.store.upsert_approval(expired)
  with pytest.raises(ValueError, match="expired"):
    broker.approve(approval.approval_id, ApprovalDecisionRequest(approver_id="operator-a"))
  request = request.model_copy(update={"approval_id": approval.approval_id})
  assert broker.authorize(request).reason_code == "approval_expired"


def test_legacy_approval_cannot_authorize_strict_request():
  broker, request = _setup(action="deploy")
  legacy = broker.decide(request.model_copy(update={"metadata": {}}))
  broker.approve(legacy.approval.approval_id, ApprovalDecisionRequest(approver_id="operator-a"))
  decision = broker.authorize(request.model_copy(update={"approval_id": legacy.approval.approval_id}))
  assert decision.reason_code == "approval_context_mismatch"


def test_legacy_decide_cannot_bypass_strict_approval_consumption():
  broker, request = _setup(action="deploy")
  request = _approved(broker, request)
  assert broker.decide(request.model_copy(update={"metadata": {}})).reason_code == "request_digest_required"
  assert broker.decide(request).action == "allow"
  assert broker.decide(request).reason_code == "approval_consumed"


def test_concurrent_threads_allow_only_one_approval_consumer():
  broker, request = _setup(action="deploy")
  request = _approved(broker, request)
  with ThreadPoolExecutor(max_workers=8) as pool:
    decisions = list(pool.map(broker.authorize, [request] * 8))
  assert sum(decision.action == "allow" for decision in decisions) == 1
  assert sum(decision.reason_code == "approval_consumed" for decision in decisions) == 7


def _authorize_file(path, payload):
  broker = AccessBroker(FileAccessBrokerStore(path))
  decision = broker.authorize(AccessRequest.model_validate(payload))
  return decision.action, decision.reason_code


@pytest.mark.skipif(__import__("os").name != "posix", reason="File store writes require POSIX flock")
def test_concurrent_processes_and_restart_do_not_replay_approval(tmp_path):
  path = tmp_path / "broker.json"
  broker, request = _setup(FileAccessBrokerStore(path), action="deploy")
  request = _approved(broker, request)
  with ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context("spawn")) as pool:
    results = list(pool.map(_authorize_file, [str(path)] * 2, [request.model_dump(mode="json")] * 2))
  assert sorted(results) == [("allow", "approved_high_risk_action"), ("block", "approval_consumed")]
  restarted = AccessBroker(FileAccessBrokerStore(path))
  assert restarted.authorize(request).reason_code == "approval_consumed"
  assert sum(event.event_type == "access.approval_consumed" for event in restarted.store.list_audit_events(100)) == 1


def test_failed_file_commit_never_returns_an_authorization(tmp_path, monkeypatch):
  path = tmp_path / "broker.json"
  broker, request = _setup(FileAccessBrokerStore(path), action="deploy")
  request = _approved(broker, request)
  before = path.read_bytes()

  def fail_commit():
    raise OSError("synthetic storage failure")

  monkeypatch.setattr(broker.store, "_persist", fail_commit)
  with pytest.raises(OSError, match="synthetic storage failure"):
    broker.authorize(request)
  assert path.read_bytes() == before
  assert broker.store.get_approval(request.approval_id).consumed_at is None


def test_strict_audit_does_not_copy_untrusted_request_metadata():
  broker, request = _setup()
  request.metadata["raw_body"] = "synthetic-sensitive-value"
  broker.authorize(request)
  event = broker.store.list_audit_events()[-1]
  assert "synthetic-sensitive-value" not in event.model_dump_json()
