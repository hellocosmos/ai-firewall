"""Data contracts for the built-in Agent Access Broker."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

RiskTier = Literal["low", "medium", "high"]
DelegationStatus = Literal["active", "revoked", "expired"]
ApprovalStatus = Literal["pending", "approved", "denied"]
AccessAction = Literal["allow", "block", "approval_required"]


def utc_now() -> datetime:
  return datetime.now(timezone.utc)


class AgentRecord(BaseModel):
  agent_id: str = Field(..., min_length=1)
  tenant_id: str | None = None
  owner_id: str = Field(..., min_length=1)
  sponsor_id: str | None = None
  runtime: str = Field(default="unknown", min_length=1)
  model: str | None = None
  allow_autonomous: bool = False
  allowed_actions: list[str] = Field(default_factory=list)
  allowed_tools: list[str] = Field(default_factory=list)
  allowed_resources: list[str] = Field(default_factory=list)
  risk_tier: RiskTier = "medium"
  enabled: bool = True
  metadata: dict[str, Any] = Field(default_factory=dict)
  created_at: datetime = Field(default_factory=utc_now)


class DelegationCreateRequest(BaseModel):
  delegation_id: str = Field(..., min_length=1)
  tenant_id: str | None = None
  user_id: str = Field(..., min_length=1)
  agent_id: str = Field(..., min_length=1)
  task_id: str = Field(..., min_length=1)
  purpose: str = Field(..., min_length=1)
  allowed_resources: list[str] = Field(default_factory=list)
  allowed_actions: list[str] = Field(default_factory=list)
  ttl_seconds: int = Field(default=900, ge=1, le=86_400)
  metadata: dict[str, Any] = Field(default_factory=dict)


class DelegationRecord(BaseModel):
  delegation_id: str
  tenant_id: str | None = None
  user_id: str
  agent_id: str
  task_id: str
  purpose: str
  allowed_resources: list[str] = Field(default_factory=list)
  allowed_actions: list[str] = Field(default_factory=list)
  status: DelegationStatus = "active"
  created_at: datetime = Field(default_factory=utc_now)
  expires_at: datetime
  metadata: dict[str, Any] = Field(default_factory=dict)

  def is_active(self, now: datetime | None = None) -> bool:
    current = now or utc_now()
    return self.status == "active" and self.expires_at > current


class AccessRequest(BaseModel):
  authorization_mode: Literal["delegated", "agent"] = "delegated"
  tenant_id: str | None = None
  user_id: str = ""
  agent_id: str = Field(..., min_length=1)
  agent_instance_id: str | None = None
  delegation_id: str = ""
  task_id: str = ""
  tool_name: str = Field(..., min_length=1)
  resource_id: str = Field(..., min_length=1)
  requested_action: str = Field(..., min_length=1)
  approval_id: str | None = None
  risk_score: float | None = Field(default=None, ge=0, le=1)
  metadata: dict[str, Any] = Field(default_factory=dict)


class BrokerToken(BaseModel):
  token_type: Literal["jit"] = "jit"
  token_id: str
  subject: str
  scopes: list[str]
  expires_at: datetime
  tenant_id: str | None = None
  request_digest: str | None = None


class ApprovalRecord(BaseModel):
  authorization_mode: Literal["delegated", "agent"] = "delegated"
  approval_id: str
  status: ApprovalStatus = "pending"
  tenant_id: str | None = None
  user_id: str
  agent_id: str
  delegation_id: str
  task_id: str
  tool_name: str
  resource_id: str
  requested_action: str
  agent_instance_id: str | None = None
  request_digest: str | None = None
  expires_at: datetime | None = None
  consumed_at: datetime | None = None
  reason: str
  created_at: datetime = Field(default_factory=utc_now)
  decided_at: datetime | None = None
  approver_id: str | None = None
  comment: str | None = None
  metadata: dict[str, Any] = Field(default_factory=dict)

  def matches(self, request: AccessRequest) -> bool:
    return (
      self.authorization_mode == request.authorization_mode
      and self.tenant_id == request.tenant_id
      and self.user_id == request.user_id
      and self.agent_id == request.agent_id
      and self.delegation_id == request.delegation_id
      and self.task_id == request.task_id
      and self.tool_name == request.tool_name
      and self.resource_id == request.resource_id
      and self.requested_action == request.requested_action
      and (
        self.request_digest is None
        or (
          self.request_digest == request.metadata.get("request_digest")
          and self.agent_instance_id == request.agent_instance_id
        )
      )
    )


class ApprovalDecisionRequest(BaseModel):
  approver_id: str = Field(..., min_length=1)
  comment: str | None = None


class AccessDecision(BaseModel):
  decision_id: str
  action: AccessAction
  reason_code: str
  reason: str
  tenant_id: str | None = None
  user_id: str
  agent_id: str
  delegation_id: str
  task_id: str
  tool_name: str
  resource_id: str
  requested_action: str
  token: BrokerToken | None = None
  approval: ApprovalRecord | None = None
  metadata: dict[str, Any] = Field(default_factory=dict)
  created_at: datetime = Field(default_factory=utc_now)


class AuditEvent(BaseModel):
  event_id: str
  event_type: str
  created_at: datetime = Field(default_factory=utc_now)
  payload: dict[str, Any] = Field(default_factory=dict)
