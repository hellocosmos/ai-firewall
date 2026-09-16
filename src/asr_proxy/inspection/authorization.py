"""공개 인가 계약. Enterprise 구현은 별도 배포의 entry point로 연결한다."""
from importlib.metadata import entry_points
from typing import Any

from pydantic import BaseModel, Field

from .contracts import InspectionConfig


class AuthorizationRequest(BaseModel):
  tenant_id: str
  user_id: str
  agent_id: str
  delegation_id: str
  task_id: str
  tool_name: str
  resource_id: str
  requested_action: str
  agent_instance_id: str | None = None
  approval_id: str | None = None
  metadata: dict[str, Any] = Field(default_factory=dict)


def load_authorizer(config: InspectionConfig):
  if config.edition == "community":
    return None
  providers = list(entry_points(group="trapdefense.authorizers", name="enterprise"))
  if len(providers) != 1:
    raise RuntimeError("enterprise_authorizer_not_installed_or_ambiguous")
  provider = providers[0].load()(config)
  if not callable(getattr(provider, "authorize", None)) or not callable(getattr(provider, "evaluate", None)):
    raise RuntimeError("invalid_enterprise_authorizer")
  return provider
