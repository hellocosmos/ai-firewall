"""Synthetic local demo helpers; never distribute the trusted-hop key to agents.

The sender simulates an authenticated decryptor/forwarding hop. It is not an
application SDK integration and does not implement TLS interception or steering.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
import yaml

from .contracts import HttpMessage, InspectionConfig
from .identity import ATTESTATION_HEADER, AttestationVerifier, sign_attestation
from .protocol import encode_json, strict_json

FORMAT = "trapdefense-community-demo-v1"
DEMO_IDENTITY = {"source_id": "demo-decryptor"}

MAX_BODY = 1_048_576
APPROVAL_ID = re.compile(r"apv_[A-Za-z0-9_-]{1,100}\Z")


class DemoError(ValueError):
  """Fixed non-sensitive CLI error code."""


def _private_create(path: Path, content: bytes):
  flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
  descriptor = os.open(path, flags, 0o600)
  with os.fdopen(descriptor, "wb") as output:
    output.write(content)


def demo_config(state: Path) -> InspectionConfig:
  return InspectionConfig.model_validate({
    "access_broker_enabled": False, "trusted_sources": ["demo-decryptor"],
    "routes": [{"authority": "example.test", "path": "/mcp", "method": "POST",
      "protocol": "mcp", "tools": {
        "notes.read": {"action": "read", "resource": "notes"},
        "notes.delete": {"action": "delete", "resource": "notes", "effect": "block"},
      }, "redact_fields": ["/params/arguments/message"]}],
    "allowed_egress_origins": [], "max_body_bytes": MAX_BODY, "pii_action": "redact",
    "attestation_max_age_seconds": 60,
    "nonce_db": str(state / "nonces.sqlite"),
    "broker_store": str(state / "broker.json"),
    "audit_path": str(state / "inspection.jsonl"),
  })


def init_demo(state_dir: str | Path) -> dict:
  requested = Path(state_dir).expanduser()
  if requested.exists() or requested.is_symlink():
    raise DemoError("state_directory_already_exists")
  state = requested.resolve()
  state.mkdir(mode=0o700, parents=True, exist_ok=False)
  _private_create(state / "attestation.key", secrets.token_bytes(48))
  _private_create(state / "demo.json", encode_json({"format": FORMAT, "identity": DEMO_IDENTITY}))
  _private_create(state / "inspector.yaml", yaml.safe_dump(demo_config(state).model_dump(), sort_keys=False).encode())
  _private_create(state / "inspection.jsonl", b"")
  return {"state_dir": str(state), "product": "open_source", "scope": "synthetic_local_only"}


def load_demo(state_dir: str | Path) -> Path:
  state = Path(state_dir).expanduser().resolve()
  if not state.is_dir() or state.stat().st_mode & 0o077:
    raise DemoError("private_demo_state_required")
  for name in ("demo.json", "attestation.key", "inspector.yaml"):
    path = state / name
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
      raise DemoError("private_demo_files_required")
  if strict_json((state / "demo.json").read_bytes()) != {"format": FORMAT, "identity": DEMO_IDENTITY}:
    raise DemoError("not_a_synthetic_demo_state")
  return state


def validate_endpoint(endpoint: str) -> str:
  try:
    parsed = urlsplit(endpoint)
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
        or parsed.username is not None or parsed.password is not None
        or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
        or parsed.port is None or not 1 <= parsed.port <= 65535):
      raise ValueError()
  except ValueError:
    raise DemoError("endpoint_must_be_literal_loopback_http_base_url") from None
  return f"http://127.0.0.1:{parsed.port}/mcp"


def signed_demo_request(client: httpx.Client, endpoint: str, state_dir: str | Path,
                        message: str, tool: str = "read", approval_id: str | None = None):
  if tool not in {"read", "delete"}:
    raise DemoError("unsupported_demo_tool")
  target = validate_endpoint(endpoint)
  state = load_demo(state_dir)
  if approval_id is not None and not APPROVAL_ID.fullmatch(approval_id):
    raise DemoError("invalid_demo_approval_id")
  body = encode_json({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
    "name": f"notes.{tool}", "arguments": {"message": message, "count": 1},
  }})
  if len(body) > MAX_BODY:
    raise DemoError("demo_body_limit_exceeded")
  # Build first: httpx defaults are application headers and must be attested too.
  request = client.build_request("POST", target,
    headers={"host": "example.test", "content-type": "application/json"}, content=body)
  observed = HttpMessage("POST", "example.test", "/mcp", dict(request.headers), body)
  identity = dict(DEMO_IDENTITY)
  if approval_id is not None:
    identity["approval_id"] = approval_id
  request.headers[ATTESTATION_HEADER] = sign_attestation(
    observed, identity, (state / "attestation.key").read_bytes(), nonce=uuid4().hex,
  )
  return request


def send_demo(endpoint: str, state_dir: str | Path, message: str, tool: str = "read",
              approval_id: str | None = None, *, transport=None) -> dict:
  with httpx.Client(timeout=10, trust_env=False, follow_redirects=False, transport=transport) as client:
    request = signed_demo_request(client, endpoint, state_dir, message, tool, approval_id)
    response = client.send(request)
  # Deliberately do not print request/response bodies, headers, keys or tokens.
  output = {"http_status": response.status_code, "response_bytes": len(response.content),
            "tool": f"notes.{tool}", "authority": "example.test"}
  try:
    value = response.json()
  except ValueError:
    value = None
  if isinstance(value, dict):
    if value.get("mode") in {"inline", "mirror"}:
      output["mode"] = value["mode"]
    if type(value.get("enforcement_applied")) is bool:
      output["enforcement_applied"] = value["enforcement_applied"]
    if value.get("decision") in {"allow", "block", "redact", "approval_required", "unknown"}:
      output["decision"] = value["decision"]
    if "error" in value:
      output["error_response"] = True
    approval = value.get("approval_id")
    if isinstance(approval, str) and APPROVAL_ID.fullmatch(approval):
      output["approval_id"] = approval
    demo = value.get("demo")
    if isinstance(demo, dict):
      count = demo.get("count")
      output["upstream_count"] = count if type(count) is int and 0 <= count <= 1_000_000_000 else None
      output["upstream_message_redacted"] = demo.get("message_redacted") is True
  return output


def _read_demo_body(handler: BaseHTTPRequestHandler) -> bytes:
  lengths = handler.headers.get_all("Content-Length", [])
  encodings = handler.headers.get_all("Transfer-Encoding", [])
  if len(lengths) > 1 or len(encodings) > 1 or (lengths and encodings):
    raise DemoError("invalid_demo_framing")
  if encodings:
    if encodings[0].lower() != "chunked":
      raise DemoError("unsupported_demo_framing")
    chunks, total = [], 0
    while True:
      line = handler.rfile.readline(81)
      if len(line) > 80 or not line.endswith(b"\r\n"):
        raise DemoError("invalid_demo_chunk")
      size = int(line.split(b";", 1)[0].strip(), 16)
      if size < 0 or total + size > MAX_BODY:
        raise DemoError("demo_body_limit_exceeded")
      if size == 0:
        for _ in range(32):
          trailer = handler.rfile.readline(8193)
          if trailer == b"\r\n":
            return b"".join(chunks)
          if not trailer or len(trailer) > 8192:
            break
        raise DemoError("unsupported_demo_trailers")
      chunk = handler.rfile.read(size)
      if len(chunk) != size or handler.rfile.read(2) != b"\r\n":
        raise DemoError("incomplete_demo_body")
      chunks.append(chunk)
      total += size
  size = int(lengths[0]) if lengths else 0
  if not 0 <= size <= MAX_BODY:
    raise DemoError("demo_body_limit_exceeded")
  body = handler.rfile.read(size)
  if len(body) != size:
    raise DemoError("incomplete_demo_body")
  return body


def create_demo_upstream(port: int = 18090) -> ThreadingHTTPServer:
  """A no-op destination: records summary metrics, never stores the original body."""
  lock = threading.Lock()
  summary = {"count": 0, "body_bytes": 0, "tool": None, "message_redacted": False}

  class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def setup(self):
      super().setup()
      self.connection.settimeout(5)

    def log_message(self, *args):
      pass

    def reply(self, code, value):
      payload = encode_json(value)
      self.send_response(code)
      self.send_header("Content-Type", "application/json")
      self.send_header("Content-Length", str(len(payload)))
      self.end_headers()
      self.wfile.write(payload)

    def do_GET(self):
      if self.path != "/_demo/stats":
        self.reply(404, {"error": "not_found"})
        return
      with lock:
        self.reply(200, dict(summary))

    def do_POST(self):
      try:
        if self.path != "/mcp":
          raise DemoError("unmapped_demo_path")
        body = _read_demo_body(self)
        value = strict_json(body)
        if not isinstance(value, dict) or not isinstance(value.get("params"), dict):
          raise DemoError("invalid_demo_call")
        params = value["params"]
        tool = params["name"]
        if (value.get("jsonrpc") != "2.0" or value.get("method") != "tools/call"
            or tool not in {"notes.read", "notes.delete"}):
          raise DemoError("unsupported_demo_call")
        if not isinstance(params.get("arguments"), dict):
          raise DemoError("invalid_demo_arguments")
        message = params["arguments"].get("message", "")
        if not isinstance(message, str):
          raise DemoError("invalid_demo_message")
        with lock:
          summary.update(count=summary["count"] + 1, body_bytes=len(body), tool=tool,
                         message_redacted="[REDACTED]" in message)
          current = dict(summary)
        self.reply(200, {"jsonrpc": "2.0", "id": 1,
          "result": {"content": [{"type": "text", "text": "Synthetic tool completed"}], "isError": False},
          "demo": current})
      except (ValueError, KeyError, TypeError, OSError):
        self.close_connection = True
        try:
          self.reply(400, {"error": "invalid_synthetic_request"})
        except OSError:
          pass

  server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
  server.daemon_threads = True
  return server


def main(argv=None) -> int:
  parser = argparse.ArgumentParser(description="Synthetic local trusted-hop inspection demonstration")
  commands = parser.add_subparsers(dest="command", required=True)
  init = commands.add_parser("init", help="Create new private demo state; never overwrite")
  init.add_argument("--state-dir", required=True)
  upstream = commands.add_parser("upstream", help="Run a loopback-only no-op tool destination")
  upstream.add_argument("--port", type=int, default=18090)
  send = commands.add_parser("send", help="Simulate a trusted decryptor hop; synthetic input only")
  send.add_argument("--endpoint", required=True)
  send.add_argument("--state-dir", required=True)
  send.add_argument("--message", default="hello")
  send.add_argument("--tool", choices=["read", "delete"], default="read")
  args = parser.parse_args(argv)
  try:
    if args.command == "init":
      result = init_demo(args.state_dir)
    elif args.command == "send":
      result = send_demo(args.endpoint, args.state_dir, args.message, args.tool)
    else:
      if not 1 <= args.port <= 65535:
        raise DemoError("invalid_demo_port")
      server = create_demo_upstream(args.port)
      print(json.dumps({"upstream": f"127.0.0.1:{server.server_port}", "scope": "synthetic_local_only"}))
      try:
        server.serve_forever()
      except KeyboardInterrupt:
        pass
      finally:
        server.server_close()
      return 0
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0
  except DemoError as exc:
    print(json.dumps({"error": str(exc)}), file=sys.stderr)
  except httpx.HTTPError:
    print(json.dumps({"error": "local_endpoint_unavailable"}), file=sys.stderr)
  except (ValueError, KeyError, OSError):
    print(json.dumps({"error": "demo_operation_failed"}), file=sys.stderr)
  return 2


if __name__ == "__main__":
  raise SystemExit(main())
