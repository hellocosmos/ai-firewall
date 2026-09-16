"""로컬 TLS 테스트 helper의 프레이밍·고정 목적지·정리 경계를 검증한다.

TLS 연결은 loopback만 사용하며 인증서는 해당 클라이언트에만 명시적으로 신뢰시킨다.
실장비 인증, 운영 인증서 설치, 외부 호스트 연결을 수행하는 테스트가 아니다.
"""
# ruff: noqa: SIM117 - nested scopes make TLS socket and listener teardown explicit
from __future__ import annotations

import http.client
import os
import socket
import ssl
import time

import pytest
from test_dataplane_transport import http_fixture
from tls_simulation import LIMIT, tls_hop

pytestmark = pytest.mark.skipif(
  os.environ.get("TD_RUNTIME_SMOKE") != "1",
  reason="set TD_RUNTIME_SMOKE=1 for local TLS safety checks",
)


def _connect(hop):
  context = ssl.create_default_context(cafile=str(hop["ca_file"]))
  transport = socket.create_connection(("127.0.0.1", hop["port"]), timeout=3)
  try:
    encrypted = context.wrap_socket(transport, server_hostname="127.0.0.1")
  except BaseException:
    transport.close()
    raise
  encrypted.settimeout(3)
  return encrypted


def _request(headers, body=b"", *, target=b"/mcp"):
  return b"POST " + target + b" HTTP/1.1\r\n" + headers + b"\r\n\r\n" + body


def _exchange(hop, request):
  with _connect(hop) as encrypted:
    encrypted.sendall(request)
    response = http.client.HTTPResponse(encrypted)
    try:
      response.begin()
      body = response.read()
      return response.status, body
    finally:
      response.close()


def _wait_for_observations(hop, count):
  deadline = time.monotonic() + 3
  while (len(hop["observations"]) < count or "status" not in hop["observations"][count - 1]):
    if time.monotonic() >= deadline:
      pytest.fail("TLS rejection did not complete within the bounded local wait")
    time.sleep(0.01)
  assert len(hop["observations"]) == count


def test_tls_rejects_duplicate_length_and_ambiguous_transfer_framing(tmp_path):
  headers = [
    b"Content-Length: 0\r\nContent-Length: 0",
    b"Content-Length: 0\r\nContent-Length: 1",
    b"Content-Length: 0\r\nTransfer-Encoding: chunked",
    b"Transfer-Encoding: chunked\r\nTransfer-Encoding: chunked",
    b"Transfer-Encoding: gzip, chunked",
  ]
  with http_fixture() as (upstream, received):
    with tls_hop(tmp_path, upstream) as hop:
      for framing in headers:
        assert _exchange(hop, _request(b"Host: example.test\r\n" + framing)) == (400, b"")
    assert received == []
    assert len(hop["observations"]) == len(headers)
    assert all(not event["forwarded"] for event in hop["observations"])


def test_tls_incomplete_content_length_and_chunks_never_reach_upstream(tmp_path):
  requests = [
    _request(b"Host: example.test\r\nContent-Length: 5", b"ab"),
    _request(b"Host: example.test\r\nTransfer-Encoding: chunked", b"5\r\nab"),
  ]
  with http_fixture() as (upstream, received):
    with tls_hop(tmp_path, upstream) as hop:
      for index, request in enumerate(requests, 1):
        with _connect(hop) as encrypted:
          encrypted.sendall(request)
        # TCP close makes the short body explicit; do not wait for the read timeout.
        _wait_for_observations(hop, index)
        event = hop["observations"][-1]
        assert not event["forwarded"]
        assert event["status"] == 400 and event["reason"] == "incomplete_request"
      assert received == []
      status, _ = _exchange(hop, _request(b"Host: example.test\r\nContent-Length: 2", b"ok"))
      assert status == 207
    assert len(received) == 1 and received[0]["body"] == b"ok"


def test_tls_one_mib_body_boundary_covers_fixed_and_chunked_framing(tmp_path):
  exact = b"a" * LIMIT
  oversized = [
    _request(f"Host: example.test\r\nContent-Length: {LIMIT + 1}".encode()),
    _request(b"Host: example.test\r\nTransfer-Encoding: chunked",
             f"{LIMIT + 1:x}\r\n".encode()),
    _request(b"Host: example.test\r\nTransfer-Encoding: chunked",
             f"{LIMIT:x}\r\n".encode() + exact + b"\r\n1\r\nz\r\n0\r\n\r\n"),
  ]
  with http_fixture() as (upstream, received):
    with tls_hop(tmp_path, upstream) as hop:
      status, _ = _exchange(hop, _request(
        f"Host: example.test\r\nContent-Length: {LIMIT}".encode(), exact))
      assert status == 207
      for request in oversized:
        assert _exchange(hop, request) == (413, b"")
    assert len(received) == 1 and received[0]["body"] == exact
    assert len(hop["observations"]) == 4
    assert hop["observations"][0]["body_bytes"] == LIMIT
    assert all(not event["forwarded"] and event["reason"] == "body_limit_exceeded"
               for event in hop["observations"][1:])


def test_tls_rejects_invalid_authorities_and_absolute_targets_without_dynamic_routing(tmp_path):
  cases = [
    (b"user@example.test", b"/mcp"),
    (b"example.test/path", b"/mcp"),
    (b"example.test?query", b"/mcp"),
    (b"example.test#fragment", b"/mcp"),
    (b"example.test", b"http://127.0.0.1:1/mcp"),
    (b"example.test", b"//127.0.0.1:1/mcp"),
  ]
  with http_fixture() as (upstream, received):
    with tls_hop(tmp_path, upstream) as hop:
      for authority, target in cases:
        request = _request(b"Host: " + authority + b"\r\nContent-Length: 0", target=target)
        assert _exchange(hop, request) == (400, b"")
      assert received == []
      # A syntactically valid Host is metadata, never a destination selector.
      status, _ = _exchange(hop, _request(b"Host: 127.0.0.1:1\r\nContent-Length: 2", b"ok"))
      assert status == 207
    assert len(received) == 1 and received[0]["headers"]["host"] == "127.0.0.1:1"
    assert len(hop["observations"]) == len(cases) + 1
    assert all(not event["forwarded"] for event in hop["observations"][:-1])


def test_tls_rejects_non_port_upstream_arguments_before_creating_resources(tmp_path):
  invalid_ports = ["192.0.2.1:443", ("192.0.2.1", 443), "443", True, 0, 65536]
  for invalid in invalid_ports:
    with pytest.raises(ValueError, match="fixed_loopback_upstream_port_required"):
      with tls_hop(tmp_path, invalid):
        pytest.fail("an invalid destination must be rejected before the listener starts")
  assert list(tmp_path.iterdir()) == []


def test_tls_context_removes_private_certificate_material_and_closes_listener(tmp_path):
  with http_fixture() as (upstream, received):
    with tls_hop(tmp_path, upstream) as hop:
      certificate = hop["ca_file"]
      private_key = hop["certificate_key_file"]
      assert certificate.exists() and private_key.exists()
      assert private_key.stat().st_mode & 0o077 == 0
      assert private_key.parent.stat().st_mode & 0o077 == 0
      with _connect(hop) as encrypted:
        assert encrypted.getpeername() == ("127.0.0.1", hop["port"])
        encrypted.sendall(_request(b"Host: example.test\r\nContent-Length: 0"))
        response = http.client.HTTPResponse(encrypted)
        try:
          response.begin()
          assert response.status == 207
          response.read()
        finally:
          response.close()
    assert len(received) == 1
    assert not certificate.exists() and not private_key.exists()
    assert not private_key.parent.exists()
    with pytest.raises(OSError):
      with socket.create_connection(("127.0.0.1", hop["port"]), timeout=0.5):
        pytest.fail("TLS listener remains reachable after context exit")
