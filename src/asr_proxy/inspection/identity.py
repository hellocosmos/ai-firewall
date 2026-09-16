from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sqlite3
import time
from pathlib import Path

from .contracts import HttpMessage, InspectionError

ATTESTATION_HEADER = "x-td-attestation"
IDENTITY_FIELDS = ("tenant_id", "user_id", "agent_id", "delegation_id", "task_id")
# Application headers are bound by default, including custom API keys and action overrides.
# Reserved forwarding context is removed by the adapter and is NOT an application identity.
TRANSPORT_HEADERS = {"host", "content-length", "transfer-encoding", "connection", "te",
                     "trailer", "keep-alive", "upgrade"}


def reserved_header(name: str) -> bool:
  return name.startswith(("x-td-", "x-asr-", "x-forwarded-", "x-envoy-")) or name in {
    "forwarded", "x-request-id",
  }


def application_headers(headers: dict[str, str]) -> dict[str, str]:
  return {key: value for key, value in headers.items()
          if key not in TRANSPORT_HEADERS and not key.startswith(":") and not reserved_header(key)}


def request_digest(message: HttpMessage) -> str:
  value = {
    "method": message.method, "authority": message.authority, "path": message.path,
    "headers": application_headers(message.headers),
    "body_sha256": hashlib.sha256(message.body).hexdigest(),
  }
  return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def sign_attestation(message: HttpMessage, identity: dict, key: bytes, *, nonce: str,
                     now: int | None = None, ttl: int = 60) -> str:
  """Trusted-hop helper, not a client identity proof. Never distribute this key to agents."""
  issued = int(time.time()) if now is None else now
  payload = {**identity, "request_digest": request_digest(message), "nonce": nonce,
             "issued_at": issued, "expires_at": issued + ttl}
  raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
  encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")
  signature = hmac.new(key, encoded.encode(), hashlib.sha256).hexdigest()
  return encoded + "." + signature


class AttestationVerifier:
  def __init__(self, key: bytes, nonce_db: str, *, max_age: int = 60,
               required_fields: tuple[str, ...] = IDENTITY_FIELDS):
    if len(key) < 32:
      raise ValueError("attestation_key_requires_32_bytes")
    self.key, self.max_age, self.nonce_db = key, max_age, nonce_db
    self.required_fields = required_fields
    Path(nonce_db).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(nonce_db) as db:
      db.execute("CREATE TABLE IF NOT EXISTS nonces (nonce TEXT PRIMARY KEY, expires INTEGER)")
      db.execute("CREATE INDEX IF NOT EXISTS nonces_expires ON nonces (expires)")
    Path(nonce_db).chmod(0o600)

  def verify(self, message: HttpMessage, *, consume: bool) -> dict:
    try:
      encoded, signature = message.headers[ATTESTATION_HEADER].split(".")
      if len(encoded) > 8192 or len(signature) != 64:
        raise ValueError()
      expected = hmac.new(self.key, encoded.encode(), hashlib.sha256).hexdigest()
      if not hmac.compare_digest(expected, signature):
        raise ValueError()
      payload = json.loads(base64.b64decode(encoded + "=" * (-len(encoded) % 4),
                                          altchars=b"-_", validate=True))
      now = int(time.time())
      if not isinstance(payload, dict):
        raise TypeError()
      if not all(isinstance(payload.get(k), str) and 0 < len(payload[k]) <= 256
                 for k in (*self.required_fields, "nonce")):
        raise ValueError()
      issued, expires = payload["issued_at"], payload["expires_at"]
      if type(issued) is not int or type(expires) is not int:
        raise ValueError()
      if issued > now + 5 or now >= expires or expires <= issued or now - issued > self.max_age:
        raise ValueError()
      if expires - issued > self.max_age:
        raise ValueError()
      if not hmac.compare_digest(payload["request_digest"], request_digest(message)):
        raise ValueError()
    except (KeyError, ValueError, TypeError, UnicodeError):
      raise InspectionError("untrusted_or_mismatched_identity") from None
    if consume:
      try:
        with sqlite3.connect(self.nonce_db, timeout=5) as db:
          db.execute("DELETE FROM nonces WHERE expires < ?", (now - 5,))
          db.execute("INSERT INTO nonces VALUES (?, ?)", (payload["nonce"], expires))
      except sqlite3.IntegrityError:
        raise InspectionError("attestation_replay") from None
    return payload
