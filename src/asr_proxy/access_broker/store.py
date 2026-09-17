"""In-memory and crash-safe local file stores for the Access Broker."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Iterator

try:
  import fcntl
except ImportError:  # pragma: no cover - Windows is not a supported file-store writer
  fcntl = None

from asr_proxy.access_broker.models import (
  AgentRecord,
  ApprovalRecord,
  AuditEvent,
  DelegationRecord,
)


class InMemoryAccessBrokerStore:
  def __init__(self) -> None:
    self._lock = RLock()
    self.agents: dict[str, AgentRecord] = {}
    self.delegations: dict[str, DelegationRecord] = {}
    self.approvals: dict[str, ApprovalRecord] = {}
    self.audit_events: list[AuditEvent] = []

  @contextmanager
  def transaction(self) -> Iterator[None]:
    """Serialize a complete authorization within this process."""
    with self._lock:
      yield

  @contextmanager
  def read_transaction(self) -> Iterator[None]:
    """Read a consistent snapshot without modifying broker state."""
    with self._lock:
      yield

  def upsert_agent(self, agent: AgentRecord) -> AgentRecord:
    with self._lock:
      self.agents[agent.agent_id] = agent
    return agent

  def get_agent(self, agent_id: str) -> AgentRecord | None:
    return self.agents.get(agent_id)

  def list_agents(self) -> list[AgentRecord]:
    return sorted(self.agents.values(), key=lambda agent: agent.created_at, reverse=True)

  def create_delegation(self, delegation: DelegationRecord) -> DelegationRecord:
    with self._lock:
      self.delegations[delegation.delegation_id] = delegation
    return delegation

  def get_delegation(self, delegation_id: str) -> DelegationRecord | None:
    return self.delegations.get(delegation_id)

  def list_delegations(self) -> list[DelegationRecord]:
    return sorted(
      self.delegations.values(),
      key=lambda delegation: delegation.created_at,
      reverse=True,
    )

  def upsert_approval(self, approval: ApprovalRecord) -> ApprovalRecord:
    with self._lock:
      self.approvals[approval.approval_id] = approval
    return approval

  def get_approval(self, approval_id: str) -> ApprovalRecord | None:
    return self.approvals.get(approval_id)

  def list_approvals(self) -> list[ApprovalRecord]:
    return sorted(
      self.approvals.values(),
      key=lambda approval: approval.created_at,
      reverse=True,
    )

  def append_audit_event(self, event: AuditEvent) -> AuditEvent:
    with self._lock:
      self.audit_events.append(event)
    return event

  def list_audit_events(self, limit: int = 100) -> list[AuditEvent]:
    return self.audit_events[-limit:]


class FileAccessBrokerStore(InMemoryAccessBrokerStore):
  def __init__(self, path: str | Path) -> None:
    self.path = Path(path).resolve()
    self._transaction_depth = 0
    self._dirty = False
    super().__init__()
    self._load()

  @contextmanager
  def transaction(self) -> Iterator[None]:
    """Lock, refresh, and commit one transaction on a local POSIX filesystem."""
    with self._lock:
      if self._transaction_depth:
        yield
        return
      if fcntl is None:
        raise RuntimeError("FileAccessBrokerStore writes require POSIX flock support.")
      self.path.parent.mkdir(parents=True, exist_ok=True)
      lock_path = self.path.with_suffix(f"{self.path.suffix}.lock")
      with lock_path.open("a+b") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
          self._load()
          self._transaction_depth = 1
          self._dirty = False
          try:
            yield
            if self._dirty:
              self._persist()
          except BaseException:
            self._load()
            raise
          finally:
            self._transaction_depth = 0
            self._dirty = False
        finally:
          fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

  @contextmanager
  def read_transaction(self) -> Iterator[None]:
    with self._lock:
      if not self._transaction_depth:
        # Writers replace the complete JSON snapshot atomically. Reading
        # does not create a lock file, write audit, or consume approvals.
        self._load()
      yield

  def upsert_agent(self, agent: AgentRecord) -> AgentRecord:
    with self.transaction():
      saved = super().upsert_agent(agent)
      self._dirty = True
      return saved

  def create_delegation(self, delegation: DelegationRecord) -> DelegationRecord:
    with self.transaction():
      saved = super().create_delegation(delegation)
      self._dirty = True
      return saved

  def upsert_approval(self, approval: ApprovalRecord) -> ApprovalRecord:
    with self.transaction():
      saved = super().upsert_approval(approval)
      self._dirty = True
      return saved

  def append_audit_event(self, event: AuditEvent) -> AuditEvent:
    with self.transaction():
      saved = super().append_audit_event(event)
      self._dirty = True
      return saved

  def _load(self) -> None:
    if not self.path.exists():
      self.agents = {}
      self.delegations = {}
      self.approvals = {}
      self.audit_events = []
      return
    raw = json.loads(self.path.read_text(encoding="utf-8"))
    self.agents = {
      item["agent_id"]: AgentRecord.model_validate(item)
      for item in raw.get("agents", [])
    }
    self.delegations = {
      item["delegation_id"]: DelegationRecord.model_validate(item)
      for item in raw.get("delegations", [])
    }
    self.approvals = {
      item["approval_id"]: ApprovalRecord.model_validate(item)
      for item in raw.get("approvals", [])
    }
    self.audit_events = [
      AuditEvent.model_validate(item)
      for item in raw.get("audit_events", [])
    ]

  def _persist(self) -> None:
    self.path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
      "agents": [agent.model_dump(mode="json") for agent in self.agents.values()],
      "delegations": [
        delegation.model_dump(mode="json")
        for delegation in self.delegations.values()
      ],
      "approvals": [
        approval.model_dump(mode="json")
        for approval in self.approvals.values()
      ],
      "audit_events": [
        event.model_dump(mode="json")
        for event in self.audit_events
      ],
    }
    temp_path: Path | None = None
    try:
      with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=self.path.parent,
        prefix=f".{self.path.name}.", suffix=".tmp", delete=False,
      ) as output:
        temp_path = Path(output.name)
        json.dump(payload, output, indent=2, sort_keys=True)
        output.flush()
        os.fsync(output.fileno())
      temp_path.replace(self.path)
      directory_fd = os.open(self.path.parent, os.O_RDONLY)
      try:
        os.fsync(directory_fd)
      finally:
        os.close(directory_fd)
    finally:
      if temp_path is not None:
        temp_path.unlink(missing_ok=True)
