"""Bounded, offline detection of credentials in inspected content."""

from __future__ import annotations

import base64
import json
import math
import re
from collections.abc import Iterator
from urllib.parse import parse_qsl

from .budget import check_deadline


_TOKEN_PATTERNS = tuple(re.compile(pattern) for pattern in (
  r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
  r"(?<![0-9A-Z])(?:AKIA|ASIA)[0-9A-Z]{16}(?![0-9A-Z])",
  r"(?<![A-Za-z0-9_])gh[pousr]_[A-Za-z0-9]{30,255}(?![A-Za-z0-9])",
  r"(?<![A-Za-z0-9_])github_pat_[A-Za-z0-9_]{40,255}(?![A-Za-z0-9_])",
  r"(?<![A-Za-z0-9_-])AIza[0-9A-Za-z_-]{35}(?![0-9A-Za-z_-])",
  r"(?<![A-Za-z0-9-])xox[baprs]-[0-9A-Za-z-]{20,255}(?![0-9A-Za-z-])",
  r"(?<![A-Za-z0-9_])(?:sk|rk)_(?:live|test)_[0-9A-Za-z]{16,255}(?![0-9A-Za-z])",
  r"(?<![A-Za-z0-9_-])sk-(?:proj-)?[0-9A-Za-z_-]{20,255}(?![0-9A-Za-z_-])",
))

_JWT_PATTERN = re.compile(
  r"(?<![A-Za-z0-9_-])(eyJ[A-Za-z0-9_-]{3,508})\."
  r"([A-Za-z0-9_-]{2,8192})\.([A-Za-z0-9_-]{16,2048})(?![A-Za-z0-9_-])"
)
_ASSIGNMENT_PATTERN = re.compile(
  r"(?i)(?:[\"']?)(api[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token|"
  r"auth[_-]?token|bearer[_-]?token|private[_-]?key|storage[_-]?key|account[_-]?key|"
  r"sas[_-]?token|password|authorization)(?:[\"']?)\s*[:=]\s*"
  r"(?:[\"']?)([^\s\"'&,}]{12,512})"
)
_SENSITIVE_FIELDS = {
  "apikey", "clientsecret", "accesstoken", "refreshtoken", "authtoken", "bearertoken",
  "privatekey", "storagekey", "accountkey", "sastoken", "password", "authorization",
}
_PLACEHOLDER_WORDS = (
  "example", "sample", "placeholder", "redacted", "changeme", "replace-me", "replace_me",
  "your-api-key", "your_api_key", "your-secret", "your_secret", "test-only", "synthetic",
  "dummy", "not-a-secret", "not_a_secret",
)


def _normalize_field(value: str) -> str:
  return "".join(character for character in value.lower() if character.isalnum())


def _decode_json_segment(value: str) -> dict | None:
  try:
    padding = "=" * (-len(value) % 4)
    decoded = base64.urlsafe_b64decode(value + padding)
    parsed = json.loads(decoded)
  except (ValueError, UnicodeError, json.JSONDecodeError):
    return None
  return parsed if isinstance(parsed, dict) else None


def _contains_valid_jwt(text: str) -> bool:
  for match in _JWT_PATTERN.finditer(text):
    check_deadline()
    header = _decode_json_segment(match.group(1))
    payload = _decode_json_segment(match.group(2))
    algorithm = header.get("alg") if header else None
    if (isinstance(algorithm, str) and algorithm and algorithm.lower() != "none"
        and payload is not None):
      return True
  return False


def _looks_secret(value: str) -> bool:
  candidate = value.strip().strip("\"'")
  if candidate.lower().startswith(("bearer ", "basic ")):
    candidate = candidate.split(" ", 1)[1]
  lowered = candidate.lower()
  if len(candidate) < 16 or len(candidate) > 4096:
    return False
  if (lowered in _PLACEHOLDER_WORDS or any(word in lowered for word in _PLACEHOLDER_WORDS)
      or lowered.startswith(("your-", "your_", "test-", "test_"))
      or candidate.startswith(("${", "{{", "<")) or candidate.endswith(">")):
    return False
  if any(character.isspace() for character in candidate):
    return False
  counts = {}
  for character in candidate:
    counts[character] = counts.get(character, 0) + 1
  entropy = -sum((count / len(candidate)) * math.log2(count / len(candidate))
                 for count in counts.values())
  classes = sum(bool(re.search(pattern, candidate)) for pattern in (
    r"[a-z]", r"[A-Z]", r"[0-9]", r"[^A-Za-z0-9]",
  ))
  return len(counts) >= 8 and classes >= 2 and entropy >= 3.25


def _query_candidates(text: str) -> Iterator[str]:
  for token in re.split(r"[\s\"'<>]+", text):
    check_deadline()
    token = token.strip("()[]{}.,;")
    if "?" in token:
      yield token.split("?", 1)[1].split("#", 1)[0]
    elif "=" in token and "&" in token:
      yield token.split("#", 1)[0].removeprefix("&")


def _contains_azure_sas(text: str) -> bool:
  for query in _query_candidates(text):
    try:
      pairs = parse_qsl(query, keep_blank_values=True, max_num_fields=128)
    except ValueError:
      continue
    values = {key.lower(): value for key, value in pairs}
    context = {"se", "sp", "ss", "srt", "sr", "si", "skoid", "sktid"}
    if (values.get("sv") and _looks_secret(values.get("sig", ""))
        and len(context.intersection(values)) >= 2):
      return True
  return False


def _contains_secret_text(text: str) -> bool:
  check_deadline()
  if any(pattern.search(text) for pattern in _TOKEN_PATTERNS):
    return True
  if _contains_valid_jwt(text) or _contains_azure_sas(text):
    return True
  return any(_looks_secret(match.group(2)) for match in _ASSIGNMENT_PATTERN.finditer(text))


def contains_secret(value, *, sensitive_field: bool = False) -> bool:
  """Return True for a recognized credential without returning or retaining its value."""
  check_deadline()
  if isinstance(value, dict):
    for key, child in value.items():
      check_deadline()
      key_sensitive = isinstance(key, str) and _normalize_field(key) in _SENSITIVE_FIELDS
      if contains_secret(child, sensitive_field=key_sensitive):
        return True
    return False
  if isinstance(value, list):
    return any(contains_secret(child, sensitive_field=sensitive_field) for child in value)
  if not isinstance(value, str):
    return False
  return _contains_secret_text(value) or (sensitive_field and _looks_secret(value))
