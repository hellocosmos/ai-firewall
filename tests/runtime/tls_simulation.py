"""로컬 TLS 종료 모의 장비. 투명 TLS MITM·인증서 발급·IdP 검증 구현이 아니다.

임시 자체서명 인증서의 신뢰는 테스트 클라이언트가 명시적으로 지정한다. 시스템
신뢰 저장소는 변경하지 않으며, 선택적인 신원은 테스트가 주입한 신뢰 홉 컨텍스트다.
실제 고객의 신원을 이 helper가 독립적으로 확인했다는 의미가 아니다.
"""
from __future__ import annotations

import contextlib
import hashlib
import http.client
import re
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

from asr_proxy.inspection.contracts import HttpMessage
from asr_proxy.inspection.identity import IDENTITY_FIELDS, reserved_header, sign_attestation

LIMIT = 1_048_576
TIMEOUT = 10
HOP_HEADERS = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
               "te", "trailer", "transfer-encoding", "upgrade", "content-length"}
TOKEN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+")


class _Rejected(ValueError):
  def __init__(self, reason: str, status: int = 400):
    self.reason, self.status = reason, status


def _close(connection):
  try:
    connection.shutdown(socket.SHUT_RDWR)
  except OSError:
    pass
  connection.close()


def _read_exact(handler, length, deadline):
  result = bytearray()
  while len(result) < length:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
      raise _Rejected("request_timeout", 408)
    handler.connection.settimeout(remaining)
    part = handler.rfile.read1(min(length - len(result), 65536))
    if not part:
      raise _Rejected("incomplete_request")
    result.extend(part)
  return bytes(result)


def _chunk_line(handler, deadline):
  line = bytearray()
  while not line.endswith(b"\r\n"):
    if len(line) >= 4096:
      raise _Rejected("invalid_chunk_framing")
    line.extend(_read_exact(handler, 1, deadline))
  return bytes(line)


def _body(handler, headers):
  deadline = time.monotonic() + TIMEOUT
  if "content-length" in headers and "transfer-encoding" in headers:
    raise _Rejected("ambiguous_framing")
  if "transfer-encoding" in headers:
    if headers["transfer-encoding"].lower() != "chunked":
      raise _Rejected("unsupported_transfer_encoding")
    body = bytearray()
    while True:
      line = _chunk_line(handler, deadline)[:-2]
      size_text, _, extension = line.partition(b";")
      if not re.fullmatch(rb"[0-9a-fA-F]+", size_text) or len(size_text) > 16:
        raise _Rejected("invalid_chunk_framing")
      if any(value < 32 or value > 126 for value in extension):
        raise _Rejected("invalid_chunk_framing")
      size = int(size_text, 16)
      if len(body) + size > LIMIT:
        raise _Rejected("body_limit_exceeded", 413)
      if size == 0:
        if _chunk_line(handler, deadline) != b"\r\n":
          raise _Rejected("unsupported_trailers")
        return bytes(body)
      body.extend(_read_exact(handler, size, deadline))
      if _read_exact(handler, 2, deadline) != b"\r\n":
        raise _Rejected("invalid_chunk_framing")
  length = headers.get("content-length", "0")
  if not re.fullmatch(r"[0-9]+", length) or len(length) > 16:
    raise _Rejected("invalid_content_length")
  size = int(length)
  if size > LIMIT:
    raise _Rejected("body_limit_exceeded", 413)
  return _read_exact(handler, size, deadline)


def _request_headers(handler):
  headers = {}
  for name, value in handler.headers.items():
    name = name.lower()
    if name in headers or not TOKEN.fullmatch(name):
      raise _Rejected("ambiguous_headers")
    if any(ord(char) == 127 or (ord(char) < 32 and char != "\t") for char in value):
      raise _Rejected("invalid_header_value")
    headers[name] = value
  if sum(len(k) + len(v) for k, v in headers.items()) > 65536:
    raise _Rejected("header_limit_exceeded", 431)
  authority = headers.get("host", "")
  if not authority or any(char.isspace() or char in "/\\?#@" for char in authority):
    raise _Rejected("invalid_authority")
  tokens = {value.strip().lower() for value in headers.get("connection", "").split(",") if value.strip()}
  if tokens - {"close", "keep-alive"} or "upgrade" in headers:
    raise _Rejected("unsupported_connection_tokens")
  return headers


def _response(connection, method):
  response = connection.getresponse()
  headers = response.getheaders()
  lowered = [(key.lower(), value) for key, value in headers]
  if sum(len(k) + len(v) for k, v in lowered) > 65536:
    raise _Rejected("upstream_headers_exceeded", 502)
  lengths = [value for key, value in lowered if key == "content-length"]
  encodings = [value for key, value in lowered if key == "transfer-encoding"]
  if len(lengths) > 1 or len(encodings) > 1 or (lengths and encodings):
    raise _Rejected("upstream_ambiguous_framing", 502)
  if encodings and encodings[0].lower() != "chunked":
    raise _Rejected("upstream_unsupported_encoding", 502)
  if lengths and (not re.fullmatch(r"[0-9]+", lengths[0]) or len(lengths[0]) > 16):
    raise _Rejected("upstream_invalid_length", 502)
  expected = int(lengths[0]) if lengths else None
  if expected is not None and expected > LIMIT:
    raise _Rejected("upstream_body_limit", 502)
  body = bytearray()
  while True:
    chunk = response.read1(min(65536, LIMIT + 1 - len(body)))
    if not chunk:
      break
    body.extend(chunk)
    if len(body) > LIMIT:
      raise _Rejected("upstream_body_limit", 502)
  has_body = method != "HEAD" and response.status not in (204, 304) and response.status >= 200
  if has_body and expected is not None and len(body) != expected:
    raise _Rejected("upstream_incomplete_body", 502)
  nominated = {token.strip().lower() for key, value in lowered if key == "connection" for token in value.split(",")}
  output = [(key, value) for key, value in headers
            if key.lower() not in HOP_HEADERS | nominated and not reserved_header(key.lower())]
  return response.status, output, bytes(body)


@contextlib.contextmanager
def tls_hop(tmp_path, upstream_port, *, key=None, identity=None):
  """Yield a loopback-only HTTPS terminator forwarding to one fixed plaintext port.

  Returned observations contain hashes/counts/status only, never original targets,
  body bytes, credentials or signed attestations. Nonempty trailers are unsupported.
  """
  if type(upstream_port) is not int or not 1 <= upstream_port <= 65535:
    raise ValueError("fixed_loopback_upstream_port_required")
  if (key is None) != (identity is None):
    raise ValueError("key_and_identity_must_be_provided_together")
  if key is not None and (not isinstance(key, bytes) or len(key) < 32):
    raise ValueError("trusted_hop_key_requires_32_bytes")
  trusted_identity = dict(identity) if identity is not None else None
  if trusted_identity is not None and not all(isinstance(trusted_identity.get(name), str)
                                              and 0 < len(trusted_identity[name]) <= 256 for name in IDENTITY_FIELDS):
    raise ValueError("trusted_hop_identity_required")
  openssl = shutil.which("openssl")
  if not openssl:
    raise RuntimeError("system_openssl_required")
  observations = []
  parent = Path(tmp_path)
  parent.mkdir(mode=0o700, parents=True, exist_ok=True)
  with tempfile.TemporaryDirectory(prefix="tls-simulation-", dir=parent) as directory:
    private = Path(directory)
    private.chmod(0o700)
    certificate, private_key = private / "ca.pem", private / "server.key"
    private_key.touch(mode=0o600)
    try:
      subprocess.run([openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
        "-subj", "/CN=localhost", "-addext", "subjectAltName=IP:127.0.0.1,DNS:localhost,DNS:example.test",
        "-keyout", str(private_key), "-out", str(certificate)],
        check=True, timeout=30, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.SubprocessError, OSError):
      raise RuntimeError("tls_certificate_generation_failed") from None
    private_key.chmod(0o600)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.set_alpn_protocols(["http/1.1"])
    context.load_cert_chain(certificate, private_key)

    class Handler(BaseHTTPRequestHandler):
      protocol_version = "HTTP/1.1"

      def setup(self):
        super().setup()
        self.timer = threading.Timer(TIMEOUT, _close, args=(self.connection,))
        self.timer.daemon = True
        self.timer.start()

      def finish(self):
        self.timer.cancel()
        super().finish()

      def log_message(self, *args):
        pass

      def send_error(self, code, message=None, explain=None):
        # BaseHTTPRequestHandler's default error body can echo attacker-controlled text.
        self.send_response_only(code)
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

      def _handle(self):
        event = {"tls_version": self.connection.version(), "method": self.command,
                 "target_sha256": hashlib.sha256(self.path.encode("utf-8")).hexdigest(), "forwarded": False}
        observations.append(event)
        try:
          raw_target = self.raw_requestline.split(b" ", 2)[1].decode("ascii")
          if raw_target != self.path or not self.path.startswith("/") or self.path.startswith("//") or "#" in self.path:
            raise _Rejected("invalid_request_target")
          headers = _request_headers(self)
          body = _body(self, headers)
          event.update(body_bytes=len(body), body_sha256=hashlib.sha256(body).hexdigest())
          forwarded = {name: value for name, value in headers.items()
                       if name not in HOP_HEADERS and not reserved_header(name)}
          forwarded.update({"content-length": str(len(body)), "connection": "close"})
          if key is not None:
            message = HttpMessage(self.command, forwarded["host"], self.path, forwarded, body)
            forwarded["x-td-attestation"] = sign_attestation(message, trusted_identity, key, nonce=uuid4().hex)
          with contextlib.closing(http.client.HTTPConnection("127.0.0.1", upstream_port, timeout=5)) as upstream:
            upstream.putrequest(self.command, self.path, skip_host=True, skip_accept_encoding=True)
            for name, value in forwarded.items():
              upstream.putheader(name, value)
            upstream.endheaders(body)
            event["forwarded"] = True
            # A slow-drip upstream must not outlive the bounded test fixture even
            # when the original TLS client disconnects or cancels its request.
            response_timer = threading.Timer(TIMEOUT, _close, args=(upstream.sock,))
            response_timer.daemon = True
            response_timer.start()
            try:
              status, response_headers, response_body = _response(upstream, self.command)
            finally:
              response_timer.cancel()
          event.update(status=status, response_bytes=len(response_body),
                       response_sha256=hashlib.sha256(response_body).hexdigest())
          self.send_response_only(status)
          for name, value in response_headers:
            self.send_header(name, value)
          self.send_header("Content-Length", str(len(response_body)))
          self.send_header("Connection", "close")
          self.end_headers()
          if self.command != "HEAD":
            self.wfile.write(response_body)
        except _Rejected as exc:
          event.update(status=exc.status, reason=exc.reason)
          self.send_error(exc.status)
        except (OSError, ValueError, http.client.HTTPException):
          event.update(status=502, reason="tls_hop_io_failure")
          try:
            self.send_error(502)
          except OSError:
            pass
        finally:
          self.close_connection = True

      do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = _handle

    class Server(ThreadingHTTPServer):
      def __init__(self):
        super().__init__(("127.0.0.1", 0), Handler)
        self.active, self.lock = set(), threading.Lock()

      def finish_request(self, request, client_address):
        request.settimeout(3)
        try:
          with context.wrap_socket(request, server_side=True) as encrypted:
            with self.lock:
              self.active.add(encrypted)
            try:
              self.RequestHandlerClass(encrypted, client_address, self)
            finally:
              with self.lock:
                self.active.discard(encrypted)
        except OSError:
          pass

      def handle_error(self, request, client_address):
        pass  # Never print request details or exception payloads.

    server = Server()
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
      yield {"port": server.server_port, "ca_file": certificate,
             "certificate_key_file": private_key, "observations": observations}
    finally:
      server.shutdown()
      with server.lock:
        active = list(server.active)
      for connection in active:
        _close(connection)
      server.server_close()
      thread.join(timeout=3)
