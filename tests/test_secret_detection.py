from __future__ import annotations

import base64
import json

import pytest

from asr_proxy.inspection.contracts import HttpMessage, InspectionConfig, InspectionError
from asr_proxy.inspection.engine import InspectionEngine
from asr_proxy.inspection.secret_detection import contains_secret


class NoPii:
  def analyze(self, _text):
    return []


@pytest.fixture
def engine():
  return InspectionEngine(InspectionConfig(routes=[]), NoPii(), None, None)


def jwt() -> str:
  def segment(value):
    encoded = base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode())
    return encoded.rstrip(b"=").decode()

  return f"{segment({'alg': 'HS256', 'typ': 'JWT'})}.{segment({'sub': 'synthetic-user'})}." + "A1b2C3d4" * 4


@pytest.mark.parametrize("secret", [
  "AKIA" + "A1B2C3D4E5F6G7H8",
  "ASIA" + "A1B2C3D4E5F6G7H8",
  "ghp_" + "Ab3" * 12,
  "github_pat_" + "Ab3_" * 12,
  "AIza" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7R",
  "xoxb-" + "A1b2C3d4E5f6G7h8I9j0K1l2",
  "sk_live_" + "A1b2C3d4E5f6G7h8I9j0",
  "sk-proj-" + "A1b2C3d4E5f6G7h8I9j0K1l2",
  "-----BEGIN PRIVATE KEY-----\nSYNTHETIC",
])
def test_explicit_synthetic_secret_formats_are_detected(secret):
  assert contains_secret({"message": f"copy {secret}"}) is True


def test_valid_structural_jwt_is_detected_but_malformed_lookalike_is_not():
  assert contains_secret(jwt()) is True
  assert contains_secret("eyJhbGciOiJIUzI1NiJ9.not-json.A1b2C3d4E5f6G7h8") is False
  assert contains_secret("eyJhbGciOiJub25lIn0.e30.A1b2C3d4E5f6G7h8") is False


def test_azure_sas_requires_signature_version_and_sas_context():
  signature = "AbC1dEf2GhI3jKl4MnO5pQr6StU7vWx8Yz9%2B%2F%3D"
  sas = ("https://synthetic.blob.core.windows.net/demo?sv=2024-11-04&sp=r&se=2099-01-01T00%3A00%3A00Z"
         f"&sr=b&sig={signature}")
  assert contains_secret(sas) is True
  assert contains_secret("https://example.test/file?sig=ordinary-signature&download=1") is False
  assert contains_secret("https://example.test/file?sv=2024-11-04&sig=<signature>&sp=r&sr=b") is False


@pytest.mark.parametrize("field", [
  "api_key", "clientSecret", "access-token", "refresh_token", "storage_key", "password",
])
def test_sensitive_fields_require_a_non_placeholder_high_entropy_value(field):
  assert contains_secret({field: "AbC1dEf2GhI3jKl4MnO5pQr6"}) is True
  assert contains_secret({field: "YOUR-SERVER-SIDE-SECRET"}) is False
  assert contains_secret({field: "test-only"}) is False


def test_sensitive_assignment_in_text_is_detected():
  assert contains_secret("client_secret=AbC1dEf2GhI3jKl4MnO5pQr6") is True


def test_request_credential_headers_pass_but_response_headers_are_inspected(engine):
  token = "sk-proj-" + "A1b2C3d4E5f6G7h8I9j0K1l2"
  request = HttpMessage("POST", "example.test", "/api", {
    "authorization": f"Bearer {token}",
    "x-api-key": token,
  }, b"")
  engine.inspect_metadata(request)
  with pytest.raises(InspectionError, match="^secret_detected$"):
    engine.inspect_metadata(request, response=True)


def test_configured_target_credential_header_is_bound_but_not_content_scanned():
  token = "sk-proj-" + "A1b2C3d4E5f6G7h8I9j0K1l2"
  engine=InspectionEngine(InspectionConfig(routes=[],
    credential_headers=['ocp-apim-subscription-key']),NoPii(),None,None)
  request=HttpMessage('POST','example.test','/api',{
    'ocp-apim-subscription-key':token,'x-business-value':'safe'},b'')
  engine.inspect_metadata(request)
  with pytest.raises(InspectionError,match='^secret_detected$'):
    engine.inspect_metadata(request,response=True)


def test_secret_verdict_and_evidence_never_include_captured_value(engine):
  secret = "sk-proj-" + "A1b2C3d4E5f6G7h8I9j0K1l2"
  message = HttpMessage("POST", "example.test", "/api", {
    "content-type": "application/json",
  }, json.dumps({"result": secret}).encode())
  result = engine.inspect_response(message, mode="inline")
  evidence = json.dumps(result.evidence(phase="response"))
  assert (result.action, result.reason, result.body) == ("block", "secret_detected", None)
  assert secret not in evidence
