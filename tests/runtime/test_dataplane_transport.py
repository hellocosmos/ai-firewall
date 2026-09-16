"""Opt-in real data-plane compatibility tests; synthetic traffic only.

These test the proxy transport contract, NOT the production inspection engine.
Run with TD_RUNTIME_SMOKE=1 and pinned runtimes downloaded. Containers use only
random loopback published ports; temporary files contain no credentials.
"""
# ruff: noqa: SIM117 - nested fixture scopes make owned runtime teardown explicit
from __future__ import annotations

import concurrent.futures
import contextlib
import http.client
import os
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
  os.environ.get("TD_RUNTIME_SMOKE") != "1",
  reason="real runtime smoke requires TD_RUNTIME_SMOKE=1",
)

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "deploy" / "inspection"
IMAGE = "envoyproxy/envoy@sha256:b21240e552b588017072424716c0bce30000f49deed6262bde55b042b5acfd97"


def free_port():
  with socket.socket() as listener:
    listener.bind(("127.0.0.1", 0))
    return listener.getsockname()[1]


@contextlib.contextmanager
def http_fixture():
  events = []
  class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
      if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
        chunks = []
        while True:
          size = int(self.rfile.readline().split(b";", 1)[0].strip(), 16)
          if size == 0:
            while self.rfile.readline() not in {b"\r\n", b"\n", b""}:
              pass
            break
          chunks.append(self.rfile.read(size))
          assert self.rfile.read(2) == b"\r\n"
        body = b"".join(chunks)
      else:
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
      events.append({"path": self.path, "headers": dict(self.headers), "body": body})
      response = b"r" * (1048576 + 1) if b"fixture-large-response" in body else b'{"result":"fixture-secret"}'
      self.send_response(207)
      self.send_header("Content-Type", "application/json")
      self.send_header("Content-Length", str(len(response)))
      self.end_headers()
      self.wfile.write(response)

    def log_message(self, *args):
      pass

  server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
  thread = threading.Thread(target=server.serve_forever, daemon=True)
  thread.start()
  try:
    yield server.server_port, events
  finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@contextlib.contextmanager
def inspector_fixture():
  import grpc
  from envoy.service.ext_proc.v3 import external_processor_pb2 as ep
  from envoy.service.ext_proc.v3 import external_processor_pb2_grpc as service
  phases = []

  class Inspector(service.ExternalProcessorServicer):
    def Process(self, request_iterator, context):
      for request in request_iterator:
        phase = request.WhichOneof("request")
        phases.append(phase)
        if phase == "request_headers":
          yield ep.ProcessingResponse(request_headers=ep.HeadersResponse(
            response=ep.CommonResponse(header_mutation=ep.HeaderMutation(
              remove_headers=["x-td-attestation"],
            )),
          ))
        elif phase == "request_body":
          if b"fixture-block" in request.request_body.body:
            yield ep.ProcessingResponse(immediate_response=ep.ImmediateResponse(
              status={"code": 403}, body=b"fixture denied",
            ))
            return
          body = request.request_body.body.replace(b"fixture-secret", b"fixture-mask!!")
          yield ep.ProcessingResponse(request_body=ep.BodyResponse(
            response=ep.CommonResponse(body_mutation=ep.BodyMutation(body=body)),
          ))
        elif phase == "response_headers":
          yield ep.ProcessingResponse(response_headers=ep.HeadersResponse())
        elif phase == "response_body":
          body = request.response_body.body.replace(b"fixture-secret", b"fixture-mask!!")
          yield ep.ProcessingResponse(response_body=ep.BodyResponse(
            response=ep.CommonResponse(body_mutation=ep.BodyMutation(body=body)),
          ))
        else:
          context.abort(grpc.StatusCode.INVALID_ARGUMENT, "unsupported fixture phase")

  pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
  server = grpc.server(pool)
  service.add_ExternalProcessorServicer_to_server(Inspector(), server)
  port = server.add_insecure_port("127.0.0.1:0")
  server.start()
  try:
    yield port, phases
  finally:
    server.stop(0).wait(2)
    pool.shutdown(wait=True)


def docker_command():
  endpoint = subprocess.check_output([
    "docker", "context", "inspect", "desktop-linux", "--format", "{{.Endpoints.docker.Host}}",
  ], text=True).strip()
  return ["docker", "--config", str(DEPLOY / "docker-public"), "--host", endpoint]


@contextlib.contextmanager
def proxy_fixture(kind, tmp_path, inspector_port, upstream_port, mirror_port=None):
  import yaml
  listener_port = free_port()
  name = f"trapdefense-transport-{os.getpid()}-{listener_port}"
  if kind == "envoy":
    mode = "mirror" if mirror_port else "inline"
    config = yaml.safe_load((DEPLOY / f"envoy-{mode}.yaml").read_text())
    container_port = config["static_resources"]["listeners"][0]["address"]["socket_address"]["port_value"]
    hcm = config["static_resources"]["listeners"][0]["filter_chains"][0]["filters"][0]["typed_config"]
    # Docker publishes a port before Envoy workers are ready. This test-only
    # direct response avoids racing readiness or contaminating inspector events.
    ready_route = {"match": {"path": "/__transport_ready"}, "direct_response": {"status": 200}}
    if not mirror_port:
      ready_route["typed_per_filter_config"] = {"envoy.filters.http.ext_proc": {
        "@type": "type.googleapis.com/envoy.extensions.filters.http.ext_proc.v3.ExtProcPerRoute",
        "disabled": True,
      }}
    hcm["route_config"]["virtual_hosts"][0]["routes"].insert(0, ready_route)
    clusters = config["static_resources"]["clusters"]
    ports = {"trapdefense_inspector": inspector_port, "local_upstream": upstream_port, "mirror_collector": mirror_port}
    for cluster in clusters:
      endpoint = cluster["load_assignment"]["endpoints"][0]["lb_endpoints"][0]["endpoint"]
      endpoint["address"]["socket_address"]["port_value"] = ports[cluster["name"]]
    config_path = tmp_path / "envoy.yaml"
    config_path.write_text(yaml.safe_dump(config))
    command = docker_command() + [
      "run", "--rm", "--pull=never", "--name", name,
      "--label", "com.trapdefense.scope=transport-test",
      "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
      "--user", "65532:65532", "--entrypoint", "/usr/local/bin/envoy",
      "--publish", f"127.0.0.1:{listener_port}:{container_port}",
      "--mount", f"type=bind,source={config_path},target=/etc/envoy/test.yaml,readonly",
      IMAGE, "--concurrency", "2", "--log-level", "error", "-c", "/etc/envoy/test.yaml",
    ]
  else:
    mode = "mirror-headers-only" if mirror_port else "inline"
    config = yaml.safe_load((DEPLOY / f"agentgateway-{mode}.yaml").read_text())
    next(iter(config["gateways"].values()))["port"] = listener_port
    config["routes"][0]["backends"][0]["host"] = f"127.0.0.1:{upstream_port}"
    if mirror_port:
      config["routes"][0]["policies"]["requestMirror"]["backend"]["host"] = f"127.0.0.1:{mirror_port}"
    else:
      config["routes"][0]["policies"]["extProc"]["host"] = f"127.0.0.1:{inspector_port}"
    config_path = tmp_path / "agentgateway.yaml"
    config_path.write_text(yaml.safe_dump(config))
    command = [str(ROOT / ".runtime-bin" / "agentgateway-v1.5.0"), "-f", str(config_path)]
  log = (tmp_path / f"{kind}.log").open("wb")
  process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
  try:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
      if process.poll() is not None:
        pytest.fail(f"{kind} exited before ready; see {tmp_path / f'{kind}.log'}")
      try:
        with socket.create_connection(("127.0.0.1", listener_port), timeout=0.2):
          if kind != "envoy":
            break
        ready = http.client.HTTPConnection("127.0.0.1", listener_port, timeout=0.2)
        try:
          ready.request("GET", "/__transport_ready")
          result = ready.getresponse()
          result.read()
          if result.status == 200:
            break
        finally:
          ready.close()
      except OSError:
        time.sleep(0.05)
      except http.client.HTTPException:
        time.sleep(0.05)
    else:
      pytest.fail(f"{kind} listener did not start")
    yield listener_port
  finally:
    if kind == "envoy":
      subprocess.run(docker_command() + ["stop", "--time", "1", name],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)
    elif process.poll() is None:
      process.terminate()
    try:
      process.wait(timeout=5)
    except subprocess.TimeoutExpired:
      process.kill()
      process.wait(timeout=2)
    log.close()


def post(port, body):
  client = http.client.HTTPConnection("127.0.0.1", port, timeout=8)
  try:
    client.request("POST", "/mcp?x=%2F&z=1", body=body, encode_chunked=not isinstance(body, (bytes, str)), headers={
      "Host": "example.test", "Content-Type": "application/json",
      "x-td-attestation": "synthetic-fixture-not-a-credential",
    })
    response = client.getresponse()
    return response.status, response.read()
  finally:
    client.close()


@pytest.mark.parametrize("kind", ["agentgateway", "envoy"])
def test_full_body_mutation_and_original_http_preserved(kind, tmp_path):
  with http_fixture() as (upstream, events), inspector_fixture() as (inspector, phases):
    with proxy_fixture(kind, tmp_path, inspector, upstream) as gateway:
      status, body = post(gateway, b'{"input":"fixture-secret"}')
      assert status == 207
      assert body == b'{"result":"fixture-mask!!"}'
      assert len(events) == 1
      assert events[0]["path"] == "/mcp?x=%2F&z=1"
      headers = {name.lower(): value for name, value in events[0]["headers"].items()}
      assert headers["host"] == "example.test"
      assert "x-td-attestation" not in headers
      assert events[0]["body"] == b'{"input":"fixture-mask!!"}'
      assert phases == ["request_headers", "request_body", "response_headers", "response_body"]


@pytest.mark.parametrize("kind", ["agentgateway", "envoy"])
def test_chunked_request_inspected_as_one_full_body(kind, tmp_path):
  with http_fixture() as (upstream, events), inspector_fixture() as (inspector, phases):
    with proxy_fixture(kind, tmp_path, inspector, upstream) as gateway:
      status, _ = post(gateway, [b'{"input":"fixture-', b'se', b'cret"}'])
      assert status == 207
      assert len(events) == 1
      assert events[0]["body"] == b'{"input":"fixture-mask!!"}'
      assert phases.count("request_body") == 1


@pytest.mark.parametrize("kind", ["agentgateway", "envoy"])
def test_immediate_block_does_not_reach_upstream(kind, tmp_path):
  with http_fixture() as (upstream, events), inspector_fixture() as (inspector, phases):
    with proxy_fixture(kind, tmp_path, inspector, upstream) as gateway:
      status, _ = post(gateway, b'{"input":"fixture-block"}')
      assert status == 403
      assert not events
      assert phases == ["request_headers", "request_body"]


@pytest.mark.parametrize("kind", ["agentgateway", "envoy"])
def test_unavailable_inspector_does_not_reach_upstream(kind, tmp_path):
  with http_fixture() as (upstream, events):
    with proxy_fixture(kind, tmp_path, free_port(), upstream) as gateway:
      status, _ = post(gateway, b'{"input":"normal"}')
      assert 500 <= status <= 599
      assert not events


@pytest.mark.parametrize("kind", ["agentgateway", "envoy"])
def test_oversized_request_does_not_reach_upstream(kind, tmp_path):
  with http_fixture() as (upstream, events), inspector_fixture() as (inspector, _phases):
    with proxy_fixture(kind, tmp_path, inspector, upstream) as gateway:
      status, _ = post(gateway, b"x" * (1048576 + 1))
      assert status in {413, 500, 502}
      assert not events


@pytest.mark.parametrize("kind", ["agentgateway", "envoy"])
def test_oversized_response_is_not_released(kind, tmp_path):
  with http_fixture() as (upstream, events), inspector_fixture() as (inspector, _phases):
    with proxy_fixture(kind, tmp_path, inspector, upstream) as gateway:
      status, body = post(gateway, b'{"input":"fixture-large-response"}')
      assert status >= 400
      assert len(body) < 1000
      assert len(events) == 1


def test_native_mirror_header_only_limit_is_explicit(tmp_path):
  with http_fixture() as (upstream, events), http_fixture() as (collector, copies):
    with proxy_fixture("agentgateway", tmp_path, None, upstream, collector) as gateway:
      status, body = post(gateway, b'{"input":"fixture-block"}')
      assert status == 207
      assert body == b'{"result":"fixture-secret"}'
      deadline = time.monotonic() + 3
      while not copies and time.monotonic() < deadline:
        time.sleep(0.01)
      assert len(events) == len(copies) == 1
      # Pinned v1.5.0 httpproxy.rs uses Body::empty() for mirrors. This is NOT
      # evidence that content inspection works; it is a regression boundary.
      assert events[0]["body"] == b'{"input":"fixture-block"}'
      assert copies[0]["body"] == b""
      assert copies[0]["path"] == "/mcp?x=%2F&z=1"
      copy_headers = {k.lower(): v for k, v in copies[0]["headers"].items()}
      original_headers = {k.lower(): v for k, v in events[0]["headers"].items()}
      assert copy_headers["host"] == "example.test"
      assert copy_headers["x-td-attestation"] == "synthetic-fixture-not-a-credential"
      assert "x-td-attestation" not in original_headers


def test_envoy_request_mirror_body_and_attestation_preserved(tmp_path):
  with http_fixture() as (upstream, events), http_fixture() as (collector, copies):
    with proxy_fixture("envoy", tmp_path, None, upstream, collector) as gateway:
      status, body = post(gateway, b'{"input":"fixture-block"}')
      assert status == 207
      assert body == b'{"result":"fixture-secret"}'
      deadline = time.monotonic() + 3
      while not copies and time.monotonic() < deadline:
        time.sleep(0.01)
      assert len(events) == len(copies) == 1
      assert events[0]["body"] == copies[0]["body"] == b'{"input":"fixture-block"}'
      assert copies[0]["path"] == events[0]["path"] == "/mcp?x=%2F&z=1"
      copy_headers = {k.lower(): v for k, v in copies[0]["headers"].items()}
      original_headers = {k.lower(): v for k, v in events[0]["headers"].items()}
      assert copy_headers["host"] == original_headers["host"] == "example.test"
      assert copy_headers["x-td-attestation"] == "synthetic-fixture-not-a-credential"
      assert "x-td-attestation" not in original_headers


def test_envoy_mirror_failure_does_not_block_original(tmp_path):
  with http_fixture() as (upstream, events):
    with proxy_fixture("envoy", tmp_path, None, upstream, free_port()) as gateway:
      status, body = post(gateway, b'{"input":"fixture-block"}')
      assert status == 207
      assert body == b'{"result":"fixture-secret"}'
      assert len(events) == 1
      assert events[0]["body"] == b'{"input":"fixture-block"}'
