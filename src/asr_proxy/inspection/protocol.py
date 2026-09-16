from __future__ import annotations

import base64
import json
import math
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import unquote, urlsplit

from .contracts import HttpMessage, InspectionConfig, InspectionError, RouteRule

_ASCII_CONTROLS = re.compile(r"[\x00-\x1f\x7f]")


def strict_json(raw: bytes, max_depth: int = 32, max_nodes: int = 8192):
  def pairs(values):
    result = {}
    for key, value in values:
      if key in result:
        raise InspectionError("duplicate_json_key")
      result[key] = value
    return result

  def invalid(_):
    raise InspectionError("nonfinite_json_number")

  try:
    parsed = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid)
    nodes = 0
    def check(value, depth):
      nonlocal nodes
      nodes += 1
      if nodes > max_nodes:
        raise InspectionError("json_node_limit_exceeded")
      if depth > max_depth:
        raise InspectionError("json_depth_exceeded")
      if isinstance(value, float) and not math.isfinite(value):
        invalid(value)
      if isinstance(value, dict):
        for child in value.values():
          check(child, depth + 1)
      elif isinstance(value, list):
        for child in value:
          check(child, depth + 1)
    check(parsed, 0)
    return parsed
  except (UnicodeError, ValueError, RecursionError) as exc:
    if isinstance(exc, InspectionError):
      raise
    raise InspectionError("invalid_json") from None


def encode_json(value) -> bytes:
  return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def pointer(value, path: str):
  if not path.startswith("/"):
    raise InspectionError("invalid_resource_mapping")
  try:
    for part in path[1:].split("/"):
      key = part.replace("~1", "/").replace("~0", "~")
      value = value[int(key)] if isinstance(value, list) else value[key]
  except (KeyError, IndexError, ValueError, TypeError):
    raise InspectionError("missing_resource") from None
  return value


def validate_message(message: HttpMessage, config: InspectionConfig):
  if not message.complete:
    raise InspectionError("incomplete_capture")
  if len(message.body) > config.max_body_bytes:
    raise InspectionError("body_limit_exceeded")
  if message.headers.get("content-encoding", "identity").lower() != "identity":
    raise InspectionError("unsupported_content_encoding")
  if "upgrade" in message.headers or message.method == "CONNECT":
    raise InspectionError("unsupported_upgrade")
  if not message.path.startswith("/") or message.path.startswith("//"):
    raise InspectionError("invalid_target")
  if any(c in message.path + message.authority for c in "\r\n\x00"):
    raise InspectionError("invalid_target")


def route_for(message: HttpMessage, config: InspectionConfig) -> RouteRule:
  # Exact routes avoid normalization drift across middleware and origins.
  path = urlsplit(message.path).path
  decoded = unquote(path)
  if ".." in decoded.split("/") or "//" in decoded or "\\" in decoded:
    raise InspectionError("ambiguous_path")
  matches = [route for route in config.routes
             if (message.authority, path, message.method) ==
             (route.authority, route.path, route.method)
             and all(message.headers.get(key.lower()) == value
                     for key, value in route.required_headers.items())]
  if len(matches) != 1:
    raise InspectionError("unmapped_route")
  route = matches[0]
  overrides = {"x-http-method-override", "x-http-method", "x-method-override",
               "x-original-url", "x-rewrite-url", "x-amz-target"}
  if (message.headers.keys() & overrides) - {key.lower() for key in route.required_headers}:
    raise InspectionError("unmapped_action_override_header")
  return route


def decode_mcp_header(value: str) -> str:
  if value.startswith("=?base64?") and value.endswith("?="):
    try:
      return base64.b64decode(value[9:-2], validate=True).decode("utf-8")
    except (ValueError, UnicodeError):
      raise InspectionError("mcp_header_body_mismatch") from None
  if value != value.strip(" \t") or any(ord(c) > 126 or (ord(c) < 32 and c != "\t") for c in value):
    raise InspectionError("mcp_header_body_mismatch")
  return value


def _header_parameters(message: HttpMessage, rule, value):
  seen = set()
  for name, path in rule.header_parameters.items():
    name = name.lower()
    if name in seen or not re.fullmatch(r"mcp-param-[!#$%&'*+.^_`|~0-9a-z-]+", name):
      raise InspectionError("invalid_mcp_header_mapping")
    seen.add(name)
    if not path.startswith("/params/arguments/") or re.search(r"~(?![01])", path):
      raise InspectionError("invalid_mcp_header_mapping")
    expected = value
    for part in path[1:].split("/"):
      if not isinstance(expected, dict):
        if expected is None:
          break
        raise InspectionError("invalid_mcp_header_mapping")
      expected = expected.get(part.replace("~1", "/").replace("~0", "~"))
    actual = message.headers.get(name)
    if expected is None:
      if actual is not None:
        raise InspectionError("mcp_header_body_mismatch")
      continue
    if actual is None:
      raise InspectionError("mcp_header_body_mismatch")
    decoded = decode_mcp_header(actual)
    if type(expected) is int:
      try:
        numeric = re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", decoded)
        matched = bool(numeric) and abs(expected) <= 2**53 - 1 and Decimal(decoded) == expected
      except InvalidOperation:
        matched = False
    elif type(expected) is bool:
      matched = decoded == ("true" if expected else "false")
    elif isinstance(expected, str):
      matched = decoded == expected
    else:
      raise InspectionError("invalid_mcp_header_parameter")
    if not matched:
      raise InspectionError("mcp_header_body_mismatch")


def semantics(message: HttpMessage, route: RouteRule, value) -> tuple[str, str, str]:
  if route.protocol == "mcp":
    if not isinstance(value, dict) or value.get("jsonrpc") != "2.0":
      raise InspectionError("unsupported_mcp_envelope")
    version = message.headers.get("mcp-protocol-version", "2025-03-26")
    if version not in route.mcp_versions:
      raise InspectionError("unsupported_mcp_version")
    params = value.get("params", {})
    if not isinstance(params, dict):
      raise InspectionError("invalid_mcp_arguments")
    metadata = params.get("_meta", {})
    if not isinstance(metadata, dict):
      raise InspectionError("invalid_mcp_metadata")
    body_version = metadata.get("io.modelcontextprotocol/protocolVersion")
    if (version == "2026-07-28" or body_version is not None) and body_version != version:
      raise InspectionError("mcp_header_body_mismatch")
    method = value.get("method")
    if not isinstance(method, str):
      raise InspectionError("invalid_mcp_method")
    if message.headers.get("mcp-method", None if version == "2026-07-28" else method) != method:
      raise InspectionError("mcp_header_body_mismatch")
    if method == "tools/call":
      if not isinstance(params, dict) or not isinstance(params.get("arguments", {}), dict):
        raise InspectionError("invalid_mcp_arguments")
      tool = params.get("name")
      if not isinstance(tool, str):
        raise InspectionError("mcp_header_body_mismatch")
    else:
      # Explicit control-method grants support both old initialize and stateless MCP.
      tool = method
    if method in ("tools/call", "resources/read", "prompts/get"):
      expected_name = params.get("uri" if method == "resources/read" else "name")
      name = message.headers.get("mcp-name")
      if not isinstance(expected_name, str) or not expected_name:
        raise InspectionError("mcp_header_body_mismatch")
      if name is None:
        if version == "2026-07-28":
          raise InspectionError("mcp_header_body_mismatch")
      elif decode_mcp_header(name) != expected_name:
        raise InspectionError("mcp_header_body_mismatch")
    rule = route.tools.get(tool)
    if rule is None:
      raise InspectionError("unmapped_tool")
    if method == "tools/call":
      _header_parameters(message, rule, value)
  else:
    tool, rule = route.tool, route.rule
    if rule is None:
      raise InspectionError("unmapped_http_action")
  resource = pointer(value, rule.resource_pointer) if rule.resource_pointer else rule.resource
  if not isinstance(resource, str) or not resource or len(resource) > 2048:
    raise InspectionError("invalid_resource")
  return tool, rule.action, resource


def iter_strings(value):
  if isinstance(value, dict):
    for key, child in value.items():
      yield key
      yield from iter_strings(child)
  elif isinstance(value, list):
    for child in value:
      yield from iter_strings(child)
  elif isinstance(value, str):
    yield value


def check_egress(value, config: InspectionConfig):
  for text in iter_strings(value):
    # Full nested URL-valued fields; prose URLs are scanned separately by signatures.
    candidate = text.strip()
    normalized = _ASCII_CONTROLS.sub("", candidate)
    decoded = unquote(normalized)
    looks_like_url = decoded.lower().startswith(("http:", "https:", "//"))
    if looks_like_url and (candidate != normalized or decoded != normalized):
      raise InspectionError("ambiguous_nested_url")
    if candidate.startswith("//") or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", candidate) and not candidate.lower().startswith(("http://", "https://")):
      raise InspectionError("unsupported_nested_url_scheme")
    if candidate.lower().startswith(("http:", "https:")):
      try:
        url = urlsplit(candidate)
        if not url.hostname or url.username or url.password or url.fragment:
          raise ValueError()
        hostname = url.hostname.encode("idna").decode().lower()
        if ":" in hostname:
          hostname = f"[{hostname}]"
        port = url.port or (443 if url.scheme == "https" else 80)
        origin = f"{url.scheme.lower()}://{hostname}:{port}"
      except (ValueError, UnicodeError):
        raise InspectionError("invalid_nested_url") from None
      if origin not in config.allowed_egress_origins:
        raise InspectionError("egress_not_allowed")
