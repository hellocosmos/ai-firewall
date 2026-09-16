"""Identity binding, protocol ambiguity, and detection-only capture boundaries."""
from __future__ import annotations

import base64
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("grpc")
pytest.importorskip("envoy.service.ext_proc.v3.external_processor_pb2")
pytest.importorskip("regex")

from asr_proxy.inspection.contracts import (
  HttpMessage,
  InspectionConfig,
  InspectionError,
  RouteRule,
  ToolRule,
  Verdict,
)
from asr_proxy.inspection.engine import InspectionEngine
from asr_proxy.inspection.identity import AttestationVerifier, request_digest, sign_attestation
from asr_proxy.inspection.protocol import route_for, semantics, strict_json, validate_message
from asr_proxy.inspection.server import create_mirror_app, normalized_headers, remove_context

KEY = b"synthetic-attestation-key-for-unit-tests-only"
IDENTITY = {
  "tenant_id": "tenant-a", "user_id": "user-a", "agent_id": "agent-a",
  "delegation_id": "delegation-a", "task_id": "task-a", "agent_instance_id": "instance-a",
}


def _message(**changes):
  body = json.dumps({
    "jsonrpc": "2.0", "id": 1, "method": "tools/call",
    "params": {"name": "notes.read", "arguments": {"message": "normal"}},
  }).encode()
  message = HttpMessage("POST", "example.test", "/mcp?version=1",
    {"content-type": "application/json", "authorization": "Bearer synthetic-upstream-token"}, body)
  return replace(message, **changes)


def _signed(message, *, identity=None, nonce=None, **options):
  token = sign_attestation(message, identity or IDENTITY, KEY, nonce=nonce or uuid4().hex, **options)
  return replace(message, headers={**message.headers, "x-td-attestation": token})


@pytest.fixture
def verifier(tmp_path):
  return AttestationVerifier(KEY, str(tmp_path / "nonces.sqlite"))


@pytest.mark.parametrize("header", [
  "authorization", "cookie", "x-api-key", "api-key", "x-goog-api-key",
  "x-custom-service-credential", "x-tenant", "x-http-method-override", "accept",
  "mcp-protocol-version", "mcp-method", "mcp-name", "mcp-session-id",
])
def test_attestation_binds_all_end_to_end_headers(verifier, header):
  original = _message(headers={"content-type": "application/json", header: "original"})
  signed = _signed(original)
  changed = replace(signed, headers={**signed.headers, header: "substituted"})
  assert request_digest(changed) != request_digest(original)
  with pytest.raises(InspectionError, match="untrusted_or_mismatched_identity"):
    verifier.verify(changed, consume=False)


@pytest.mark.parametrize("change", [
  {"method": "DELETE"}, {"authority": "other.test"}, {"path": "/mcp?version=2"},
  {"body": b'{"different":"request"}'},
])
def test_attestation_binds_original_target_and_wire_body(verifier, change):
  signed = _signed(_message())
  with pytest.raises(InspectionError, match="untrusted_or_mismatched_identity"):
    verifier.verify(replace(signed, **change), consume=False)


def test_only_explicitly_non_application_transport_headers_are_excluded():
  original = _message()
  transformed = replace(original, headers={**original.headers,
    "content-length": str(len(original.body)), "transfer-encoding": "chunked",
    "x-request-id": "generated-by-proxy", "x-envoy-attempt-count": "1",
    "x-td-user": "forged-user", "x-asr-tool": "forged-tool",
    "forwarded": "for=synthetic", "x-forwarded-host": "untrusted.test",
  })
  assert request_digest(transformed) == request_digest(original)
  stripped = remove_context(transformed.headers)
  for header in ("x-td-user", "x-asr-tool", "forwarded", "x-forwarded-host", "x-envoy-attempt-count"):
    assert header in stripped


def test_signature_and_identity_claims_cannot_be_changed(verifier):
  signed = _signed(_message())
  encoded, signature = signed.headers["x-td-attestation"].split(".")
  payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
  payload["tenant_id"] = "forged-tenant"
  changed_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
  forged = replace(signed, headers={**signed.headers, "x-td-attestation": changed_payload + "." + signature})
  with pytest.raises(InspectionError, match="untrusted_or_mismatched_identity"):
    verifier.verify(forged, consume=False)


@pytest.mark.parametrize("offset,ttl", [(-120, 60), (120, 60), (0, 600), (0, 0)])
def test_attestation_time_window_is_bounded(verifier, offset, ttl):
  import time
  signed = _signed(_message(), now=int(time.time()) + offset, ttl=ttl)
  with pytest.raises(InspectionError, match="untrusted_or_mismatched_identity"):
    verifier.verify(signed, consume=False)


def test_mirror_does_not_consume_nonce_and_restart_does_not_restore_it(verifier):
  signed = _signed(_message())
  for _ in range(3):
    assert verifier.verify(signed, consume=False)["agent_id"] == "agent-a"
  with sqlite3.connect(verifier.nonce_db) as db:
    assert db.execute("SELECT COUNT(*) FROM nonces").fetchone()[0] == 0
  verifier.verify(signed, consume=True)
  restarted = AttestationVerifier(KEY, verifier.nonce_db)
  with pytest.raises(InspectionError, match="attestation_replay"):
    restarted.verify(signed, consume=True)


def test_concurrent_nonce_consumption_succeeds_once(verifier):
  signed = _signed(_message())
  def consume(_):
    try:
      verifier.verify(signed, consume=True)
      return "consumed"
    except InspectionError as error:
      return str(error)
  with ThreadPoolExecutor(max_workers=4) as pool:
    outcomes = list(pool.map(consume, range(4)))
  assert outcomes.count("consumed") == 1
  assert outcomes.count("attestation_replay") == 3


@pytest.mark.parametrize("headers", [
  [("Authorization", "one"), ("authorization", "two")],
  [("x-td-attestation", "one"), ("X-TD-Attestation", "two")],
  [("content-length", "1"), ("Content-Length", "2")],
  [("host", "one.test"), ("Host", "two.test")],
  [("mcp-method", "tools/call"), ("MCP-Method", "tools/list")],
])
def test_case_insensitive_duplicate_security_headers_are_rejected(headers):
  with pytest.raises(InspectionError):
    normalized_headers(headers)


@pytest.mark.parametrize("headers", [
  [("x-safe", "injected\r\nvalue")], [("bad\nname", "value")],
  [("x-safe", "nul\x00value")],
])
def test_control_characters_in_headers_are_rejected(headers):
  with pytest.raises(InspectionError):
    normalized_headers(headers)


def test_host_and_authority_cannot_disagree():
  with pytest.raises(InspectionError):
    normalized_headers([(":authority", "policy.test"), ("host", "upstream.test")])


def _route():
  return RouteRule(authority="example.test", path="/mcp", tools={
    "notes.read": ToolRule(action="read", resource="notes"),
    "initialize": ToolRule(action="connect", resource="mcp-server"),
  })


def test_legacy_headerless_mcp_uses_body_semantics():
  message = _message()
  assert semantics(message, _route(), strict_json(message.body)) == ("notes.read", "read", "notes")


def test_header_and_body_mcp_semantics_must_match():
  original = _message()
  matching = replace(original, headers={**original.headers,
    "mcp-method": "tools/call", "mcp-name": "notes.read",
  })
  assert semantics(matching, _route(), strict_json(matching.body)) == ("notes.read", "read", "notes")
  for header, forged in (("mcp-method", "tools/list"), ("mcp-name", "notes.delete")):
    changed = replace(matching, headers={**matching.headers, header: forged})
    with pytest.raises(InspectionError, match="mcp_header_body_mismatch"):
      semantics(changed, _route(), strict_json(changed.body))


def test_mcp_control_methods_need_explicit_policy_grants():
  message = _message()
  assert semantics(message, _route(), {"jsonrpc": "2.0", "method": "initialize"}) == (
    "initialize", "connect", "mcp-server",
  )
  with pytest.raises(InspectionError, match="unmapped_tool"):
    semantics(message, _route(), {"jsonrpc": "2.0", "method": "notifications/initialized"})


def _modern(*, method="tools/call", name="notes.read", arguments=None, headers=None):
  params = {"_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28"},
            "uri" if method == "resources/read" else "name": name}
  if method == "tools/call":
    params["arguments"] = arguments or {}
  body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
  encoded_name = name if name.isascii() and name == name.strip() else (
    "=?base64?" + base64.b64encode(name.encode()).decode() + "?=")
  return _message(body=body, headers={"content-type": "application/json",
    "mcp-protocol-version": "2026-07-28", "mcp-method": method, "mcp-name": encoded_name,
    **(headers or {})})


@pytest.mark.parametrize("header", ["mcp-protocol-version", "mcp-method", "mcp-name"])
def test_modern_mcp_requires_matching_metadata_headers(header):
  message = _modern()
  headers = dict(message.headers)
  del headers[header]
  with pytest.raises(InspectionError, match="mcp_header_body_mismatch"):
    semantics(replace(message, headers=headers), _route(), strict_json(message.body))


def test_unknown_or_disabled_mcp_version_is_rejected():
  message = _modern(headers={"mcp-protocol-version": "2999-01-01"})
  with pytest.raises(InspectionError, match="unsupported_mcp_version"):
    semantics(message, _route(), strict_json(message.body))
  route = _route().model_copy(update={"mcp_versions": ["2026-07-28"]})
  with pytest.raises(InspectionError, match="unsupported_mcp_version"):
    semantics(_message(), route, strict_json(_message().body))


@pytest.mark.parametrize("method,name", [
  ("tools/call", "도구"), ("resources/read", "file:///문서"), ("prompts/get", "질문"),
])
def test_modern_base64_names_are_decoded_before_authorization(method, name):
  message = _modern(method=method, name=name)
  tool = name if method == "tools/call" else method
  route = _route().model_copy(update={"tools": {tool: ToolRule(action="read", resource="notes")}})
  assert semantics(message, route, strict_json(message.body)) == (tool, "read", "notes")


@pytest.mark.parametrize("name", ["=?base64?%%%?=", "=?base64?/w==?=", " padded ", "raw한글"])
def test_malformed_or_unsafe_mcp_name_is_rejected(name):
  message = _modern(headers={"mcp-name": name})
  with pytest.raises(InspectionError, match="mcp_header_body_mismatch"):
    semantics(message, _route(), strict_json(message.body))


@pytest.mark.parametrize("body_value,header_value", [(42, "42.0"), (True, "true"), ("서울", "=?base64?7ISc7Jq4?=")])
def test_exact_mcp_parameter_mapping_accepts_valid_primitive_values(body_value, header_value):
  message = _modern(arguments={"region": body_value}, headers={"mcp-param-region": header_value})
  rule = ToolRule(action="read", resource="notes", header_parameters={"Mcp-Param-Region": "/params/arguments/region"})
  route = _route().model_copy(update={"tools": {"notes.read": rule}})
  assert semantics(message, route, strict_json(message.body)) == ("notes.read", "read", "notes")
  headers = dict(message.headers)
  del headers["mcp-param-region"]
  with pytest.raises(InspectionError, match="mcp_header_body_mismatch"):
    semantics(replace(message, headers=headers), route, strict_json(message.body))


def test_mcp_parameter_null_and_missing_omit_headers_but_unknown_headers_are_ignored():
  rule = ToolRule(action="read", resource="notes", header_parameters={"mcp-param-region": "/params/arguments/region"})
  route = _route().model_copy(update={"tools": {"notes.read": rule}})
  for arguments in ({}, {"region": None}):
    message = _modern(arguments=arguments, headers={"mcp-param-unknown": "not-authority"})
    assert semantics(message, route, strict_json(message.body)) == ("notes.read", "read", "notes")
    with pytest.raises(InspectionError, match="mcp_header_body_mismatch"):
      semantics(replace(message, headers={**message.headers, "mcp-param-region": "unexpected"}), route, strict_json(message.body))


@pytest.mark.parametrize("value,header", [(1.5, "1.5"), ([1], "1"), ({"nested": 1}, "1"),
                                         (2**53, str(2**53)), (12, "1_2"), (12, "+12"), (12, "012")])
def test_mcp_parameter_invalid_primitives_or_numeric_forms_are_rejected(value, header):
  rule = ToolRule(action="read", resource="notes", header_parameters={"mcp-param-region": "/params/arguments/region"})
  route = _route().model_copy(update={"tools": {"notes.read": rule}})
  message = _modern(arguments={"region": value}, headers={"mcp-param-region": header})
  with pytest.raises(InspectionError):
    semantics(message, route, strict_json(message.body))


@pytest.mark.parametrize("mapping,arguments", [
  ({"Mcp-Param-Region": "/params/arguments/region", "mcp-param-region": "/params/arguments/region"}, {"region": "test"}),
  ({"mcp-param-": "/params/arguments/region"}, {"region": "test"}),
  ({"mcp-param-region": "/params/arguments/region/0"}, {"region": ["test"]}),
  ({"mcp-param-region": "/params/name"}, {"region": "test"}),
  ({"mcp-param-region": "/params/arguments/reg~2ion"}, {"region": "test"}),
])
def test_invalid_mcp_header_mappings_fail_closed(mapping, arguments):
  rule = ToolRule(action="read", resource="notes", header_parameters=mapping)
  route = _route().model_copy(update={"tools": {"notes.read": rule}})
  message = _modern(arguments=arguments, headers={"mcp-param-region": "test"})
  with pytest.raises(InspectionError, match="invalid_mcp_header_mapping"):
    semantics(message, route, strict_json(message.body))


def test_mcp_exact_nested_parameter_path_and_literal_sentinel_round_trip():
  value = "=?base64?literal?="
  rule = ToolRule(action="read", resource="notes", header_parameters={"mcp-param-region": "/params/arguments/a~1b/x~0y"})
  route = _route().model_copy(update={"tools": {"notes.read": rule}})
  message = _modern(arguments={"a/b": {"x~y": value}},
                    headers={"mcp-param-region": "=?base64?" + base64.b64encode(value.encode()).decode() + "?="})
  assert semantics(message, route, strict_json(message.body)) == ("notes.read", "read", "notes")


def test_redacted_mirrored_parameter_must_be_revalidated():
  rule = ToolRule(action="read", resource="notes", header_parameters={"mcp-param-region": "/params/arguments/region"})
  route = _route().model_copy(update={"tools": {"notes.read": rule}})
  message = _modern(arguments={"region": "sensitive"}, headers={"mcp-param-region": "sensitive"})
  parsed = strict_json(message.body)
  parsed["params"]["arguments"]["region"] = "[REDACTED]"
  with pytest.raises(InspectionError, match="mcp_header_body_mismatch"):
    semantics(message, route, parsed)


@pytest.mark.parametrize("body", [
  b'[{"jsonrpc":"2.0","method":"tools/call"}]',
  b'{"jsonrpc":"2.0","method":"tools/call","params":{"name":"notes.read","arguments":[]}}',
  b'{"jsonrpc":"2.0","method":"tools/call","params":{"name":1,"arguments":{}}}',
])
def test_malformed_or_batch_mcp_requests_fail_closed(body):
  with pytest.raises(InspectionError):
    semantics(_message(body=body), _route(), strict_json(body))


@pytest.mark.parametrize("path", ["//evil.test/mcp", "/mcp/../mcp", "/mcp/%2e%2e/mcp", "/mcp\\evil", "/mcp%00"])
def test_ambiguous_or_unmapped_targets_cannot_get_a_route(path):
  config = InspectionConfig(routes=[_route()])
  with pytest.raises(InspectionError):
    message = _message(path=path)
    validate_message(message, config)
    route_for(message, config)


class _NoPII:
  def analyze(self, text):
    return []


class _BrokerSpy:
  def __init__(self):
    self.requests = []
  def evaluate(self, request):
    self.requests.append(("mirror", request))
    return SimpleNamespace(action="allow", approval=None, reason_code="allowed")
  def authorize(self, request):
    self.requests.append(("inline", request))
    return SimpleNamespace(action="allow", approval=None, reason_code="allowed")


def test_only_attested_identity_and_parsed_action_reach_the_broker(verifier):
  broker = _BrokerSpy()
  engine = InspectionEngine(InspectionConfig(routes=[_route()]), _NoPII(), verifier, broker)
  raw = _message()
  signed = _signed(replace(raw, headers={**raw.headers,
    "x-td-user": "forged-user", "x-asr-agent": "forged-agent", "x-asr-tool": "notes.delete",
    "x-td-resource": "other-resource", "x-td-action": "delete",
  }))
  assert engine.inspect_request(signed, mode="inline").action == "allow"
  mode, request = broker.requests[0]
  assert mode == "inline"
  assert request.user_id == IDENTITY["user_id"]
  assert request.agent_id == IDENTITY["agent_id"]
  assert request.agent_instance_id == IDENTITY["agent_instance_id"]
  assert (request.tool_name, request.requested_action, request.resource_id) == ("notes.read", "read", "notes")


class _CaptureEngine:
  config = InspectionConfig(routes=[], max_body_bytes=1024)
  def __init__(self):
    self.calls = []
  def inspect_request(self, message, *, mode):
    assert mode == "mirror"
    self.calls.append(("request", message))
    return Verdict("block", "synthetic_detection", "mirror")
  def inspect_response(self, message, *, mode, pii_action=None, pii_policy_scope=None):
    assert mode == "mirror"
    assert pii_action is None and pii_policy_scope is None
    self.calls.append(("response", message))
    return Verdict("allow", "synthetic_response", "mirror")


class _CaptureAudit:
  def __init__(self):
    self.events = []
  def record(self, verdict, *, phase):
    event = verdict.evidence(phase=phase)
    self.events.append(event)
    return event


def _transcript():
  return {"request": {
    "method": "POST", "authority": "example.test", "path": "/mcp",
    "headers": {"content-type": "application/json"},
    "body_base64": base64.b64encode(b"{}").decode(), "complete": True,
  }}


def test_raw_mirroring_is_request_only_and_never_claims_enforcement():
  engine, audit = _CaptureEngine(), _CaptureAudit()
  with TestClient(create_mirror_app(engine, audit)) as client:
    response = client.post("/captured?value=1", content=b"synthetic", headers={"host": "example.test"})
  assert response.status_code == 200
  result = response.json()
  assert result["visibility"] == "request_only"
  assert result["hypothetical_action"] == "would_block"
  assert result["enforcement_applied"] is False
  assert [kind for kind, _ in engine.calls] == ["request"]


def test_complete_transcript_distinguishes_request_and_response_visibility():
  engine, audit = _CaptureEngine(), _CaptureAudit()
  transcript = _transcript()
  transcript["response"] = {"headers": {"content-type": "text/plain"},
    "body_base64": base64.b64encode(b"response").decode(), "complete": True}
  with TestClient(create_mirror_app(engine, audit)) as client:
    result = client.post("/_trapdefense/observe", json=transcript).json()
  assert result["visibility"] == "request_response"
  assert result["enforcement_applied"] is False
  assert [kind for kind, _ in engine.calls] == ["request", "response"]


@pytest.mark.parametrize("invalid_headers", [None, [], "not-an-object"])
def test_invalid_capture_header_types_return_unknown_not_server_error(invalid_headers):
  engine, audit = _CaptureEngine(), _CaptureAudit()
  transcript = _transcript()
  transcript["request"]["headers"] = invalid_headers
  with TestClient(create_mirror_app(engine, audit), raise_server_exceptions=False) as client:
    result = client.post("/_trapdefense/observe", json=transcript)
  assert result.status_code == 400
  assert result.json()["decision"] == "unknown"
  assert result.json()["enforcement_applied"] is False
  assert engine.calls == []


def test_existing_nonce_store_gains_expiry_index_without_losing_replay_state(tmp_path):
  path = tmp_path / "existing.sqlite"
  with sqlite3.connect(path) as db:
    db.execute("CREATE TABLE nonces (nonce TEXT PRIMARY KEY, expires INTEGER)")
    db.execute("INSERT INTO nonces VALUES (?, ?)", ("already-seen", 4_000_000_000))
  verifier = AttestationVerifier(KEY, str(path))
  other = AttestationVerifier(KEY, str(path))
  message = _signed(_message(), nonce="already-seen")
  for instance in (verifier, other):
    with pytest.raises(InspectionError, match="attestation_replay"):
      instance.verify(message, consume=True)
  with sqlite3.connect(path) as db:
    plans = db.execute("EXPLAIN QUERY PLAN DELETE FROM nonces WHERE expires < ?", (0,)).fetchall()
    assert any("USING INDEX nonces_expires" in row[3] for row in plans)
    assert db.execute("SELECT COUNT(*) FROM nonces").fetchone()[0] == 1
