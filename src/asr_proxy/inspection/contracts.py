from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class InspectionError(ValueError):
  """Stable, non-sensitive reason code; never interpolate captured data."""


class ToolRule(BaseModel):
  model_config = ConfigDict(extra="forbid")
  action: str
  effect: Literal["allow", "block"] = "allow"
  pii_action: Literal["redact", "block"] | None = None
  resource: str | None = None
  resource_pointer: str | None = None
  # Full Mcp-Param-* header names mapped to exact JSON pointers in the body.
  header_parameters: dict[str, str] = Field(default_factory=dict)


class RouteRule(BaseModel):
  model_config = ConfigDict(extra="forbid")
  authority: str
  path: str
  method: str = "POST"
  required_headers: dict[str, str] = Field(default_factory=dict)
  protocol: Literal["http", "mcp"] = "mcp"
  pii_action: Literal["redact", "block"] | None = None
  mcp_versions: list[str] = Field(default_factory=lambda: [
    "2025-03-26", "2025-06-18", "2025-11-25", "2026-07-28",
  ])
  tool: str = "http.request"
  rule: ToolRule | None = None
  tools: dict[str, ToolRule] = Field(default_factory=dict)
  llm_provider: Literal["openai", "anthropic", "google", "openrouter"] | None = None
  allowed_models: list[str] = Field(default_factory=list)
  # JSON pointers relative to the entire body; * matches a single segment.
  redact_fields: list[str] = Field(default_factory=list)


class InspectionConfig(BaseModel):
  model_config = ConfigDict(extra="forbid")
  access_broker_enabled: bool = False
  trusted_sources: list[str] = Field(default_factory=list)
  routes: list[RouteRule]
  allowed_egress_origins: list[str] = Field(default_factory=list)
  # Request credential headers remain digest-bound but are excluded from content scanning.
  credential_headers: list[str] = Field(default_factory=list)
  max_body_bytes: int = Field(default=1_048_576, ge=1024, le=16_777_216)
  max_json_depth: int = Field(default=32, ge=1, le=100)
  pii_action: Literal["redact", "block"] = "redact"
  pii_min_score: float = Field(default=0.35, ge=0, le=1)
  attestation_max_age_seconds: int = Field(default=60, ge=1, le=300)
  nonce_db: str = ".runtime-state/nonces.sqlite"
  broker_store: str = ".runtime-state/broker.json"
  audit_path: str = ".runtime-state/inspection.jsonl"


@dataclass(frozen=True)
class HttpMessage:
  method: str
  authority: str
  path: str
  headers: dict[str, str]
  body: bytes
  complete: bool = True


@dataclass
class Verdict:
  action: Literal["allow", "block", "redact", "approval_required", "unknown"]
  reason: str
  mode: Literal["inline", "mirror"]
  body: bytes | None = field(default=None, repr=False)
  entities: list[str] = field(default_factory=list)
  coverage: str = "complete"
  identity_verified: bool = False
  request_digest: str | None = None
  approval_id: str | None = None
  tool: str | None = None
  access_action: str | None = None
  source_verified: bool = False
  authorization_scope: str = "none"
  pii_policy_action: Literal["redact", "block"] | None = None
  pii_policy_scope: Literal["global", "route", "tool"] | None = None

  def evidence(self, *, phase: str, applied: bool = False) -> dict:
    return {
      "mode": self.mode, "phase": phase, "decision": self.action,
      "hypothetical_action": f"would_{self.action}" if self.mode == "mirror" else None,
      "enforcement_applied": applied and self.mode == "inline",
      "enforcement_requested": self.mode == "inline" and self.action != "unknown",
      "reason": self.reason, "coverage": self.coverage,
      "identity_verified": self.identity_verified,
      "source_verified": self.source_verified,
      "authorization_scope": self.authorization_scope,
      "pii_policy_action": self.pii_policy_action,
      "pii_policy_scope": self.pii_policy_scope,
      "request_digest": self.request_digest, "entities": sorted(set(self.entities)),
      "tool": self.tool, "access_action": self.access_action,
      "approval_id": self.approval_id if self.mode == "inline" else None,
    }
