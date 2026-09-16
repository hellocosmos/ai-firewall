from __future__ import annotations

import json
from dataclasses import replace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from asr_proxy.inspection.authorization import load_authorizer
from asr_proxy.inspection.contracts import HttpMessage, InspectionConfig
from asr_proxy.inspection.engine import InspectionEngine
from asr_proxy.inspection.identity import AttestationVerifier, sign_attestation
from asr_proxy.inspection.pii import PiiFinding


KEY = b"synthetic-route-policy-key-32-bytes"
EMAIL = "alex@example.com"


class SyntheticPii:
  def analyze(self, text):
    start = text.find(EMAIL)
    return [] if start < 0 else [PiiFinding("EMAIL_ADDRESS", start, start + len(EMAIL), 1.0)]


@pytest.fixture
def engine(tmp_path):
  config = InspectionConfig(
    edition="community",
    trusted_sources=["decryptor-a"],
    pii_action="redact",
    nonce_db=str(tmp_path / "nonces.sqlite"),
    routes=[
      {
        "authority": "example.test",
        "path": "/mcp",
        "pii_action": "block",
        "tools": {
          "notes.read": {"action": "read", "resource": "notes", "pii_action": "redact"},
          "notes.export": {"action": "read", "resource": "notes"},
        },
        "redact_fields": ["/params/arguments/message"],
      },
      {
        "authority": "example.test",
        "path": "/submit",
        "protocol": "http",
        "tool": "form.submit",
        "pii_action": "block",
        "rule": {"action": "write", "resource": "form"},
        "redact_fields": ["/message"],
      },
      {
        "authority": "example.test",
        "path": "/global",
        "protocol": "http",
        "tool": "form.preview",
        "rule": {"action": "read", "resource": "form"},
        "redact_fields": ["/message"],
      },
    ],
  )
  verifier = AttestationVerifier(KEY, config.nonce_db, required_fields=("source_id",))
  return InspectionEngine(config, SyntheticPii(), verifier, load_authorizer(config))


def signed(path, value):
  body = json.dumps(value).encode()
  raw = HttpMessage("POST", "example.test", path, {"content-type": "application/json"}, body)
  return replace(raw, headers={**raw.headers, "x-td-attestation": sign_attestation(
    raw, {"source_id": "decryptor-a"}, KEY, nonce=uuid4().hex)})


def mcp(tool):
  return signed("/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                         "params": {"name": tool, "arguments": {"message": EMAIL}}})


def test_tool_route_and_global_pii_policy_precedence(engine):
  tool = engine.inspect_request(mcp("notes.read"), mode="inline")
  assert (tool.action, tool.pii_policy_action, tool.pii_policy_scope) == (
    "redact", "redact", "tool",
  )
  assert EMAIL.encode() not in tool.body

  route = engine.inspect_request(mcp("notes.export"), mode="inline")
  assert (route.action, route.reason, route.pii_policy_action, route.pii_policy_scope) == (
    "block", "pii_block_policy", "block", "route",
  )

  http_route = engine.inspect_request(signed("/submit", {"message": EMAIL}), mode="inline")
  assert (http_route.action, http_route.pii_policy_scope) == ("block", "route")

  global_default = engine.inspect_request(signed("/global", {"message": EMAIL}), mode="inline")
  assert (global_default.action, global_default.pii_policy_action, global_default.pii_policy_scope) == (
    "redact", "redact", "global",
  )


def test_response_uses_request_selected_policy_and_mirror_is_hypothetical(engine):
  selected = engine.inspect_request(mcp("notes.export"), mode="mirror")
  response = HttpMessage("POST", "example.test", "/mcp", {"content-type": "application/json"},
                         json.dumps({"message": EMAIL}).encode())
  result = engine.inspect_response(response, mode="mirror",
    pii_action=selected.pii_policy_action, pii_policy_scope=selected.pii_policy_scope)
  evidence = result.evidence(phase="response", applied=True)
  assert (result.action, result.reason, result.coverage) == ("block", "pii_block_policy", "complete")
  assert (evidence["pii_policy_action"], evidence["pii_policy_scope"]) == ("block", "route")
  assert evidence["hypothetical_action"] == "would_block"
  assert evidence["enforcement_applied"] is False

  redacted = engine.inspect_response(response, mode="mirror",
    pii_action="redact", pii_policy_scope="tool")
  assert redacted.action == "redact" and EMAIL.encode() not in redacted.body
  assert redacted.evidence(phase="response")["hypothetical_action"] == "would_redact"


def test_invalid_override_fails_configuration_validation():
  with pytest.raises(ValidationError):
    InspectionConfig(routes=[{"authority": "example.test", "path": "/mcp",
      "pii_action": "observe", "tools": {}}])
