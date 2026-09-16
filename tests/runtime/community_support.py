"""Synthetic Community runtime fixtures: no private package or business credentials."""
import contextlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4
import httpx
import pytest
import yaml
from test_dataplane_transport import free_port
from asr_proxy.inspection.contracts import HttpMessage
from asr_proxy.inspection.identity import sign_attestation
from asr_proxy.inspection.community_demo import init_demo
ROOT = Path(__file__).resolve().parents[2]
IDENTITY = {"source_id": "demo-decryptor", "tenant_id": "synthetic", "user_id": "synthetic",
            "agent_id": "synthetic", "delegation_id": "synthetic", "task_id": "synthetic"}


def tool_body(message="hello", tool="notes.read", **extra):
  return json.dumps({"jsonrpc": "2.0", "id": 7, "method": "tools/call",
    "params": {"name": tool, "arguments": {"message": message, "count": 1, **extra}}}).encode()

def read_body(handler):
  if handler.headers.get("Transfer-Encoding", "").lower() == "chunked":
    chunks = []
    while True:
      size = int(handler.rfile.readline().split(b";", 1)[0].strip(), 16)
      if not size:
        while handler.rfile.readline() not in (b"\r\n", b"\n", b""):
          pass
        break
      chunks.append(handler.rfile.read(size))
      assert handler.rfile.read(2) == b"\r\n"
    return b"".join(chunks)
  return handler.rfile.read(int(handler.headers.get("Content-Length", "0")))

@contextlib.contextmanager
def destination():
  received = []
  class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def do_POST(self):
      body = read_body(self)
      received.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()},
                       "body": body})
      if "response=sse" in self.path:
        media = "text/event-stream"
        chunks = [b'data: {"id":"chunk-x","choices":[{"index":0,"delta":{"content":"alex@"}}]}\n\n',
                  b'data: {"id":"chunk-x","choices":[{"index":0,"delta":{"content":"example.com"}}]}\n\n',
                  b'data: [DONE]\n\n']
      elif "response=oversize" in self.path:
        media, chunks = "text/plain", [b"a" * 1_048_577]
      elif "response=pii" in self.path:
        media, chunks = "application/json", [b'{"result":"alex@example.com"}']
      elif "response=incomplete" in self.path:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "500")
        self.end_headers()
        self.wfile.write(b'{"result":"alex@')
        self.wfile.flush()
        self.close_connection = True
        return
      elif "response=slow" in self.path:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        try:
          for _ in range(14):
            data = b'data: {"choices":[{"index":0,"delta":{"content":"alex@"}}]}\n\n'
            self.wfile.write(f"{len(data):x}\r\n".encode() + data + b"\r\n")
            self.wfile.flush()
            time.sleep(0.5)
        except (BrokenPipeError, ConnectionResetError):
          pass
        self.close_connection = True
        return
      else:
        media, chunks = "application/json", [b'{"result":"ok"}']
      self.send_response(200)
      self.send_header("Content-Type", media)
      self.send_header("Transfer-Encoding", "chunked")
      self.end_headers()
      try:
        for chunk in chunks:
          self.wfile.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n")
          self.wfile.flush()
        self.wfile.write(b"0\r\n\r\n")
      except (BrokenPipeError, ConnectionResetError):
        pass
    def log_message(self, *args):
      pass
  server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
  server.daemon_threads = True
  thread = threading.Thread(target=server.serve_forever, daemon=True)
  thread.start()
  try:
    yield server.server_port, received
  finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)

def signed_request(client, port, key, *, body=None, path="/mcp", identity=None, forged=False, chunked=False,
                   extra_headers=None):
  body = body if body is not None else tool_body()
  request = client.build_request("POST", f"http://127.0.0.1:{port}{path}",
    headers={"host": "example.test", "content-type": "application/json", **(extra_headers or {})}, content=body)
  message = HttpMessage("POST", "example.test", path, dict(request.headers), body)
  request.headers["x-td-attestation"] = sign_attestation(message, identity or IDENTITY,
    b"wrong" if forged else key, nonce=uuid4().hex)
  if chunked:
    headers = dict(request.headers)
    headers.pop("content-length", None)
    request = client.build_request("POST", str(request.url), headers=headers,
      content=iter([body[:len(body)//2], body[len(body)//2:]]))
  return request

@contextlib.contextmanager
def real_inspector(tmp_path):
  state = tmp_path / "community-state"
  init_demo(state)
  port, mirror_port = free_port(), free_port()
  key = (state / "attestation.key").read_bytes()
  with (tmp_path / "inspector.log").open("wb") as log:
    process = subprocess.Popen([sys.executable, "-m", "asr_proxy.inspection.server",
      "--config", str(state / "inspector.yaml"), "--key-file", str(state / "attestation.key"),
      "--grpc-port", str(port), "--mirror-port", str(mirror_port), "--stream-timeout", "8"],
      cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    try:
      for _ in range(160):
        if process.poll() is not None:
          pytest.fail(f"Community inspector startup failed: {tmp_path / 'inspector.log'}")
        try:
          if httpx.get(f"http://127.0.0.1:{mirror_port}/_trapdefense/health", timeout=.3).status_code == 200:
            break
        except httpx.HTTPError:
          pass
        time.sleep(.05)
      else:
        pytest.fail("Community readiness timed out")
      yield {"port": port, "mirror_port": mirror_port, "key": key,
        "audit_path": state / "inspection.jsonl", "process": process}
    finally:
      if process.poll() is None:
        process.terminate()
      try:
        process.wait(timeout=5)
      except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)
