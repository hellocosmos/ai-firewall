"""Policy engine for the built-in Agent Access Broker."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from secrets import token_urlsafe
from uuid import uuid4

from asr_proxy.access_broker.models import (
  AccessDecision,
  AccessAction,
  AccessRequest,
  AgentRecord,
  ApprovalDecisionRequest,
  ApprovalRecord,
  AuditEvent,
  BrokerToken,
  DelegationCreateRequest,
  DelegationRecord,
  utc_now,
)
from asr_proxy.access_broker.store import InMemoryAccessBrokerStore

HIGH_RISK_ACTIONS = {
  "delete",
  "deploy",
  "external_send",
  "permission_change",
  "credential_issue",
  "prod_write",
}


def _id(prefix: str) -> str:
  return f"{prefix}_{uuid4().hex[:12]}"


def _matches(value: str, patterns: list[str]) -> bool:
  return "*" in patterns or value in patterns


def _is_future(value: datetime | None, now: datetime) -> bool:
  return value is not None and value.tzinfo is not None and value > now


@dataclass(frozen=True)
class _Evaluation:
  action: AccessAction
  reason_code: str
  reason: str
  delegation: DelegationRecord | None = None
  approval: ApprovalRecord | None = None


class AccessBroker:
  def __init__(
    self,
    store: InMemoryAccessBrokerStore | None = None,
    *,
    token_ttl_seconds: int = 300,
    approval_ttl_seconds: int = 300,
  ) -> None:
    if token_ttl_seconds <= 0 or approval_ttl_seconds <= 0:
      raise ValueError("Token and approval TTLs must be positive.")
    self.store = store or InMemoryAccessBrokerStore()
    self.token_ttl_seconds = token_ttl_seconds
    self.approval_ttl_seconds = approval_ttl_seconds

  def register_agent(self, agent: AgentRecord, *, actor: dict[str, str] | None = None) -> AgentRecord:
    saved = self.store.upsert_agent(agent)
    payload = {"agent": saved.model_dump(mode="json")}
    if actor is not None:
      payload["actor"] = actor
    self._audit("access.agent_registered", payload)
    return saved

  def create_delegation(
    self, payload: DelegationCreateRequest, *, actor: dict[str, str] | None = None,
  ) -> DelegationRecord:
    now = utc_now()
    delegation = DelegationRecord(
      delegation_id=payload.delegation_id,
      tenant_id=payload.tenant_id,
      user_id=payload.user_id,
      agent_id=payload.agent_id,
      task_id=payload.task_id,
      purpose=payload.purpose,
      allowed_resources=payload.allowed_resources,
      allowed_actions=payload.allowed_actions,
      created_at=now,
      expires_at=now + timedelta(seconds=payload.ttl_seconds),
      metadata=payload.metadata,
    )
    saved = self.store.create_delegation(delegation)
    audit_payload = {"delegation": saved.model_dump(mode="json")}
    if actor is not None:
      audit_payload["actor"] = actor
    self._audit("access.delegation_created", audit_payload)
    return saved

  def decide(self, request: AccessRequest) -> AccessDecision:
    # Requests carrying a strict binding must not bypass one-time approval
    # consumption through the legacy API.
    if "request_digest" in request.metadata:
      return self.authorize(request)
    if request.approval_id:
      with self.store.read_transaction():
        approval = self.store.get_approval(request.approval_id)
        is_strict = approval is not None and approval.request_digest is not None
      if is_strict:
        return self.authorize(request)
    agent = self.store.get_agent(request.agent_id)
    if agent is None:
      return self._decision(
        request,
        action="block",
        reason_code="agent_not_registered",
        reason="Agent is not registered.",
      )

    if not agent.enabled:
      return self._decision(
        request,
        action="block",
        reason_code="agent_disabled",
        reason="Agent is disabled.",
      )

    if agent.allowed_tools and not _matches(request.tool_name, agent.allowed_tools):
      return self._decision(
        request,
        action="block",
        reason_code="tool_not_allowed_for_agent",
        reason="Tool is not allowed for agent.",
      )

    if agent.allowed_resources and not _matches(request.resource_id, agent.allowed_resources):
      return self._decision(
        request,
        action="block",
        reason_code="resource_not_allowed_for_agent",
        reason="Resource is not allowed for agent.",
      )

    delegation = self.store.get_delegation(request.delegation_id)
    if delegation is None:
      return self._decision(
        request,
        action="block",
        reason_code="delegation_not_found",
        reason="Delegation was not found.",
      )

    if not delegation.is_active():
      return self._decision(
        request,
        action="block",
        reason_code="delegation_not_active",
        reason="Delegation is expired or inactive.",
      )

    mismatch = self._delegation_mismatch(request, delegation)
    if mismatch is not None:
      reason_code, reason = mismatch
      return self._decision(request, action="block", reason_code=reason_code, reason=reason)

    if self._requires_approval(agent, request):
      approval = self._approved_record(request)
      if approval is None:
        approval = self._create_approval(request)
        return self._decision(
          request,
          action="approval_required",
          reason_code="high_risk_action_requires_approval",
          reason="The high-risk action requires human approval.",
          approval=approval,
        )

      return self._decision(
        request,
        action="allow",
        reason_code="approved_high_risk_action",
        reason="The high-risk action is approved.",
        token=self._issue_token(request, delegation),
        approval=approval,
      )

    return self._decision(
      request,
      action="allow",
      reason_code="delegation_allowed",
      reason="Agent and delegation scopes allow the action.",
      token=self._issue_token(request, delegation),
    )

  def evaluate(self, request: AccessRequest) -> AccessDecision:
    """Return a hypothetical verdict without audit, approvals, or tokens."""
    with self.store.read_transaction():
      evaluation = self._evaluate_strict(request, utc_now())
      return self._strict_decision(request, evaluation, evaluation_only=True)

  def authorize(self, request: AccessRequest) -> AccessDecision:
    """Authorize one bound request; this method never invokes a downstream tool."""
    with self.store.transaction():
      now = utc_now()
      evaluation = self._evaluate_strict(request, now)
      approval = evaluation.approval
      token = None
      if evaluation.action == "approval_required" and approval is None:
        delegation = evaluation.delegation
        assert delegation is not None
        approval = ApprovalRecord(
          approval_id=_id("apv"),
          tenant_id=request.tenant_id,
          user_id=request.user_id,
          agent_id=request.agent_id,
          agent_instance_id=request.agent_instance_id,
          delegation_id=request.delegation_id,
          task_id=request.task_id,
          tool_name=request.tool_name,
          resource_id=request.resource_id,
          requested_action=request.requested_action,
          request_digest=request.metadata["request_digest"],
          expires_at=min(
            now + timedelta(seconds=self.approval_ttl_seconds),
            delegation.expires_at,
          ),
          reason="high_risk_action_requires_approval",
          created_at=now,
        )
        self.store.upsert_approval(approval)
        self._audit("access.approval_created", {"approval": approval.model_dump(mode="json")})
      elif evaluation.action == "allow":
        assert evaluation.delegation is not None
        if approval is not None:
          approval = approval.model_copy(update={"consumed_at": now})
          self.store.upsert_approval(approval)
          self._audit(
            "access.approval_consumed",
            {"approval": approval.model_dump(mode="json")},
          )
        token = self._issue_token(request, evaluation.delegation)
      decision = self._strict_decision(
        request, evaluation, evaluation_only=False, token=token,
        approval=approval if evaluation.action != "block" else None,
      )
      self._audit("access.decision", {"decision": decision.model_dump(mode="json")})
      return decision

  def _evaluate_strict(self, request: AccessRequest, now: datetime) -> _Evaluation:
    if not request.tenant_id or not request.tenant_id.strip():
      return _Evaluation("block", "tenant_required", "Strict authorization requires a tenant.")
    digest = request.metadata.get("request_digest")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
      return _Evaluation(
        "block", "request_digest_required",
        "Strict authorization requires a lowercase SHA-256 request digest.",
      )
    agent = self.store.get_agent(request.agent_id)
    if agent is None:
      return _Evaluation("block", "agent_not_registered", "Agent is not registered.")
    if agent.tenant_id != request.tenant_id:
      return _Evaluation("block", "agent_tenant_mismatch", "Agent belongs to another tenant.")
    if not agent.enabled:
      return _Evaluation("block", "agent_disabled", "Agent is disabled.")
    if not _matches(request.tool_name, agent.allowed_tools):
      return _Evaluation("block", "tool_not_allowed_for_agent", "Tool is not allowed for agent.")
    if not _matches(request.resource_id, agent.allowed_resources):
      return _Evaluation(
        "block", "resource_not_allowed_for_agent", "Resource is not allowed for agent.",
      )
    delegation = self.store.get_delegation(request.delegation_id)
    if delegation is None:
      return _Evaluation("block", "delegation_not_found", "Delegation was not found.")
    if delegation.tenant_id != request.tenant_id:
      return _Evaluation(
        "block", "delegation_tenant_mismatch", "Delegation belongs to another tenant.",
      )
    if delegation.status != "active" or not _is_future(delegation.expires_at, now):
      return _Evaluation("block", "delegation_not_active", "Delegation is expired or inactive.")
    mismatch = self._delegation_mismatch(request, delegation)
    if mismatch is not None:
      return _Evaluation("block", *mismatch)
    if not _matches(request.resource_id, delegation.allowed_resources):
      return _Evaluation("block", "resource_not_delegated", "Resource was not delegated.")
    if not _matches(request.requested_action, delegation.allowed_actions):
      return _Evaluation("block", "action_not_delegated", "Action was not delegated.")
    if request.approval_id:
      approval = self.store.get_approval(request.approval_id)
      if approval is None:
        return _Evaluation("block", "approval_not_found", "Approval was not found.")
      if approval.request_digest is None or not approval.matches(request):
        return _Evaluation(
          "block", "approval_context_mismatch", "Approval does not match the bound request.",
        )
      if approval.consumed_at is not None:
        return _Evaluation("block", "approval_consumed", "Approval was already consumed.")
      if not _is_future(approval.expires_at, now):
        return _Evaluation("block", "approval_expired", "Approval has expired.")
      if approval.status == "denied":
        return _Evaluation("block", "approval_denied", "Approval was denied.")
      if approval.status == "pending":
        return _Evaluation(
          "approval_required", "high_risk_action_requires_approval",
          "Human approval is pending.", delegation, approval,
        )
      return _Evaluation(
        "allow", "approved_high_risk_action", "The bound action is approved.",
        delegation, approval,
      )
    if self._requires_approval(agent, request):
      return _Evaluation(
        "approval_required", "high_risk_action_requires_approval",
        "The high-risk action requires human approval.", delegation,
      )
    return _Evaluation(
      "allow", "delegation_allowed", "The bound action is delegated.", delegation,
    )

  def _strict_decision(
    self, request: AccessRequest, evaluation: _Evaluation, *, evaluation_only: bool,
    token: BrokerToken | None = None, approval: ApprovalRecord | None = None,
  ) -> AccessDecision:
    digest = request.metadata.get("request_digest")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
      digest = None
    return AccessDecision(
      decision_id=_id("dec"), action=evaluation.action,
      reason_code=evaluation.reason_code, reason=evaluation.reason,
      tenant_id=request.tenant_id, user_id=request.user_id, agent_id=request.agent_id,
      delegation_id=request.delegation_id, task_id=request.task_id,
      tool_name=request.tool_name, resource_id=request.resource_id,
      requested_action=request.requested_action, token=token, approval=approval,
      metadata={
        "agent_instance_id": request.agent_instance_id,
        "request_digest": digest,
        "evaluation_only": evaluation_only,
        "enforcementApplied": False,
      },
    )

  def approve(self, approval_id: str, payload: ApprovalDecisionRequest) -> ApprovalRecord:
    return self._set_approval_status(approval_id, payload, "approved")

  def deny(self, approval_id: str, payload: ApprovalDecisionRequest) -> ApprovalRecord:
    return self._set_approval_status(approval_id, payload, "denied")

  def _set_approval_status(
    self, approval_id: str, payload: ApprovalDecisionRequest, status: str,
  ) -> ApprovalRecord:
    with self.store.transaction():
      approval = self.store.get_approval(approval_id)
      if approval is None:
        raise ValueError(f"Unknown approval_id: {approval_id}")
      now = utc_now()
      if approval.request_digest is not None:
        if approval.consumed_at is not None or approval.status != "pending":
          raise ValueError("Strict approval is already decided or consumed.")
        if not _is_future(approval.expires_at, now):
          raise ValueError("Strict approval has expired.")
      updated = approval.model_copy(update={
        "status": status, "decided_at": now,
        "approver_id": payload.approver_id, "comment": payload.comment,
      })
      saved = self.store.upsert_approval(updated)
      self._audit(f"access.approval_{status}", {"approval": saved.model_dump(mode="json")})
      return saved

  def list_audit_events(self, limit: int = 100) -> list[AuditEvent]:
    return self.store.list_audit_events(limit)

  def _delegation_mismatch(
    self,
    request: AccessRequest,
    delegation: DelegationRecord,
  ) -> tuple[str, str] | None:
    if delegation.user_id != request.user_id:
      return "user_not_delegator", "Delegation user does not match the request."
    if delegation.agent_id != request.agent_id:
      return "agent_not_delegated", "Delegation agent does not match the request."
    if delegation.task_id != request.task_id:
      return "task_not_delegated", "Delegation task does not match the request."
    if delegation.allowed_resources and not _matches(
      request.resource_id,
      delegation.allowed_resources,
    ):
      return "resource_not_delegated", "Resource is outside the delegation scope."
    if delegation.allowed_actions and not _matches(
      request.requested_action,
      delegation.allowed_actions,
    ):
      return "action_not_delegated", "Action is outside the delegation scope."
    return None

  def _requires_approval(self, agent: AgentRecord, request: AccessRequest) -> bool:
    return agent.risk_tier == "high" or request.requested_action in HIGH_RISK_ACTIONS

  def _approved_record(self, request: AccessRequest) -> ApprovalRecord | None:
    if not request.approval_id:
      return None
    approval = self.store.get_approval(request.approval_id)
    if approval is None or approval.status != "approved":
      return None
    if not approval.matches(request):
      return None
    return approval

  def _create_approval(self, request: AccessRequest) -> ApprovalRecord:
    approval = ApprovalRecord(
      approval_id=_id("apv"),
      tenant_id=request.tenant_id,
      user_id=request.user_id,
      agent_id=request.agent_id,
      delegation_id=request.delegation_id,
      task_id=request.task_id,
      tool_name=request.tool_name,
      resource_id=request.resource_id,
      requested_action=request.requested_action,
      reason="high_risk_action_requires_approval",
    )
    saved = self.store.upsert_approval(approval)
    self._audit("access.approval_created", {"approval": saved.model_dump(mode="json")})
    return saved

  def _issue_token(self, request: AccessRequest, delegation: DelegationRecord) -> BrokerToken:
    expires_at = min(
      utc_now() + timedelta(seconds=self.token_ttl_seconds),
      delegation.expires_at,
    )
    return BrokerToken(
      token_id=f"td_jit_{token_urlsafe(12)}",
      subject=f"{request.user_id}/{request.agent_id}",
      scopes=[f"{request.resource_id}:{request.requested_action}"],
      expires_at=expires_at,
      tenant_id=request.tenant_id,
      request_digest=request.metadata.get("request_digest"),
    )

  def _decision(
    self,
    request: AccessRequest,
    *,
    action: AccessAction,
    reason_code: str,
    reason: str,
    token: BrokerToken | None = None,
    approval: ApprovalRecord | None = None,
  ) -> AccessDecision:
    decision = AccessDecision(
      decision_id=_id("dec"),
      action=action,
      reason_code=reason_code,
      reason=reason,
      tenant_id=request.tenant_id,
      user_id=request.user_id,
      agent_id=request.agent_id,
      delegation_id=request.delegation_id,
      task_id=request.task_id,
      tool_name=request.tool_name,
      resource_id=request.resource_id,
      requested_action=request.requested_action,
      token=token,
      approval=approval,
      metadata={
        "agent_instance_id": request.agent_instance_id,
        "risk_score": request.risk_score,
      },
    )
    self._audit(
      "access.decision",
      {
        "decision": decision.model_dump(mode="json"),
        "request": request.model_dump(mode="json"),
      },
    )
    return decision

  def _audit(self, event_type: str, payload: dict) -> AuditEvent:
    return self.store.append_audit_event(
      AuditEvent(
        event_id=_id("evt"),
        event_type=event_type,
        payload=payload,
      )
    )
