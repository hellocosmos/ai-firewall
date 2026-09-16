from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

pytest.importorskip("grpc")
pytest.importorskip("envoy.service.ext_proc.v3.external_processor_pb2")
pytest.importorskip("regex")

from asr_proxy.inspection.signatures import DEFAULT_PATTERNS
from asr_proxy.inspection.budget import INSPECTION_DEADLINE, check_deadline
from asr_proxy.inspection.contracts import (
  HttpMessage,
  InspectionConfig,
  InspectionError,
  RouteRule,
  ToolRule,
)
from asr_proxy.inspection.engine import InspectionEngine
from asr_proxy.inspection.protocol import strict_json
from asr_proxy.inspection.server import InspectionWorkers

ROOT = Path(__file__).resolve().parents[1]


class EmptyPii:
  def __init__(self):
    self.calls = 0

  def analyze(self, text):
    self.calls += 1
    return []


def test_quadratic_signature_input_is_bounded_in_subprocess():
  # A subprocess hard deadline prevents a regression from hanging the entire test run.
  script = '''
import json
import time
from asr_proxy.inspection.signatures import DEFAULT_PATTERNS
from asr_proxy.inspection.contracts import InspectionConfig, InspectionError
from asr_proxy.inspection.engine import InspectionEngine
original = tuple(pattern.regex for pattern in DEFAULT_PATTERNS)
engine = InspectionEngine(InspectionConfig(routes=[]), None, None, None)
started = time.monotonic()
reason = "unexpected_success"
try:
    engine._signatures("send " * 50000)
except InspectionError as error:
    reason = str(error)
print(json.dumps({"reason": reason, "elapsed": time.monotonic() - started,
                  "source_unchanged": original == tuple(p.regex for p in DEFAULT_PATTERNS)}))
'''
  completed = subprocess.run([sys.executable, "-c", script], cwd=ROOT,
    capture_output=True, text=True, timeout=2, check=True)
  result = json.loads(completed.stdout)
  assert result["reason"] == "signature_timeout"
  assert result["elapsed"] < 1
  assert result["source_unchanged"] is True


def test_signature_matchers_are_instance_owned_not_global_patches():
  originals = tuple(pattern.regex for pattern in DEFAULT_PATTERNS)
  engine = InspectionEngine(InspectionConfig(routes=[]), EmptyPii(), None, None)
  assert tuple(pattern.regex for pattern in DEFAULT_PATTERNS) == originals
  assert len(engine.signature_patterns) == sum(pattern.severity >= 2 for pattern in DEFAULT_PATTERNS)
  assert not any(copy is original for copy in engine.signature_patterns for original in originals)


def test_signature_timeout_is_not_treated_as_a_clean_response():
  engine = InspectionEngine(InspectionConfig(routes=[]), EmptyPii(), None, None)
  message = HttpMessage("POST", "example.test", "/api", {"content-type": "text/plain"}, b"send " * 50000)
  result = engine.inspect_response(message, mode="inline")
  assert result.action == "block" and result.reason == "signature_timeout"
  assert result.body is None


def test_expired_budget_prevents_starting_a_pii_scan():
  scanner = EmptyPii()
  engine = InspectionEngine(InspectionConfig(routes=[]), scanner, None, None)
  token = INSPECTION_DEADLINE.set(time.monotonic() - 1)
  try:
    with pytest.raises(InspectionError, match="^inspection_deadline$"):
      engine._find("safe")
    assert scanner.calls == 0
  finally:
    INSPECTION_DEADLINE.reset(token)


def test_expired_budget_prevents_signature_work():
  engine = InspectionEngine(InspectionConfig(routes=[]), EmptyPii(), None, None)
  token = INSPECTION_DEADLINE.set(time.monotonic() - 1)
  try:
    with pytest.raises(InspectionError, match="^inspection_deadline$"):
      engine._signatures("ignore previous instructions")
  finally:
    INSPECTION_DEADLINE.reset(token)


@pytest.mark.parametrize("mode", ["inline", "mirror"])
def test_budget_expiring_after_identity_prevents_broker_side_effect(mode):
  class Verifier:
    def verify(self, message, *, consume):
      INSPECTION_DEADLINE.set(time.monotonic() - 1)
      return {"tenant_id": "tenant-a", "user_id": "user-a", "agent_id": "agent-a",
              "delegation_id": "delegation-a", "task_id": "task-a"}

  class Broker:
    calls = 0

    def authorize(self, _):
      self.calls += 1
      raise AssertionError("expired work must not authorize")

    evaluate = authorize

  config = InspectionConfig(routes=[RouteRule(authority="example.test", path="/api",
    protocol="http", rule=ToolRule(action="read", resource="notes"), redact_fields=["/text"])])
  broker = Broker()
  engine = InspectionEngine(config, EmptyPii(), Verifier(), broker)
  token = INSPECTION_DEADLINE.set(time.monotonic() + 10)
  try:
    result = engine.inspect_request(HttpMessage("POST", "example.test", "/api",
      {"content-type": "application/json"}, b'{"text":"safe"}'), mode=mode)
    assert result.reason == "inspection_deadline"
    assert result.action == ("block" if mode == "inline" else "unknown")
    assert result.body is None and broker.calls == 0
  finally:
    INSPECTION_DEADLINE.reset(token)


def test_unset_and_future_deadlines_do_not_fail():
  token = INSPECTION_DEADLINE.set(None)
  try:
    assert check_deadline() is None
    INSPECTION_DEADLINE.set(time.monotonic() + 10)
    assert check_deadline() is None
  finally:
    INSPECTION_DEADLINE.reset(token)


def test_json_node_budget_is_exact_and_depth_still_applies():
  assert strict_json(b'{"a":[1,2]}', max_nodes=4) == {"a": [1, 2]}
  with pytest.raises(InspectionError, match="^json_node_limit_exceeded$"):
    strict_json(b'{"a":[1,2]}', max_nodes=3)
  with pytest.raises(InspectionError, match="^json_depth_exceeded$"):
    strict_json(b'[[[0]]]', max_depth=2)


def test_default_json_budget_rejects_many_tiny_values():
  assert len(strict_json(json.dumps([0] * 8191).encode())) == 8191
  with pytest.raises(InspectionError, match="^json_node_limit_exceeded$"):
    strict_json(json.dumps([0] * 8192).encode())


def test_worker_contextvar_deadlines_are_isolated_and_reset():
  async def exercise():
    workers = InspectionWorkers(maximum=2)
    parent = INSPECTION_DEADLINE.get()
    first, second = time.monotonic() + 2, time.monotonic() + 4
    result = await asyncio.gather(
      workers.run(INSPECTION_DEADLINE.get, deadline=first),
      workers.run(INSPECTION_DEADLINE.get, deadline=second),
    )
    assert result == [first, second]
    assert INSPECTION_DEADLINE.get() == parent
    assert workers.slots._value == 2

  asyncio.run(exercise())


def test_cancelled_caller_does_not_release_a_running_worker_slot():
  started, release, second_started = threading.Event(), threading.Event(), threading.Event()

  def blocked():
    started.set()
    assert release.wait(1), "test worker release timed out"
    return "first"

  def second():
    second_started.set()
    return "second"

  async def exercise():
    workers = InspectionWorkers(maximum=1)
    first = asyncio.create_task(workers.run(blocked))
    try:
      assert await asyncio.to_thread(started.wait, 1)
      first.cancel()
      with pytest.raises(asyncio.CancelledError):
        await first
      assert workers.slots._value == 0
      waiting = asyncio.create_task(workers.run(second))
      await asyncio.sleep(0.02)
      assert second_started.is_set() is False
      release.set()
      assert await asyncio.wait_for(waiting, 1) == "second"
      assert workers.slots._value == 1
    finally:
      release.set()

  asyncio.run(exercise())


def test_worker_concurrency_never_exceeds_its_limit():
  release, first_wave = threading.Event(), threading.Event()
  lock = threading.Lock()
  counts = {"active": 0, "maximum": 0}

  def callback(value):
    with lock:
      counts["active"] += 1
      counts["maximum"] = max(counts["maximum"], counts["active"])
      if counts["active"] == 4:
        first_wave.set()
    try:
      assert release.wait(1), "test worker release timed out"
      return value
    finally:
      with lock:
        counts["active"] -= 1

  async def exercise():
    workers = InspectionWorkers()
    tasks = [asyncio.create_task(workers.run(callback, i)) for i in range(8)]
    try:
      assert await asyncio.to_thread(first_wave.wait, 1)
      assert counts["active"] == 4 and workers.slots._value == 0
      release.set()
      assert await asyncio.wait_for(asyncio.gather(*tasks), 1) == list(range(8))
      assert counts["maximum"] == 4
      assert workers.slots._value == 4
    finally:
      release.set()

  asyncio.run(exercise())


def test_late_worker_failure_is_retrieved_without_logging_payload():
  started, release = threading.Event(), threading.Event()

  def failed():
    started.set()
    assert release.wait(1), "test worker release timed out"
    raise RuntimeError("synthetic private payload")

  async def exercise():
    workers = InspectionWorkers(maximum=1)
    loop = asyncio.get_running_loop()
    failures = []
    loop.set_exception_handler(lambda _, context: failures.append(context))
    task = asyncio.create_task(workers.run(failed))
    try:
      assert await asyncio.to_thread(started.wait, 1)
      task.cancel()
      with pytest.raises(asyncio.CancelledError):
        await task
      release.set()
      # A next task proves that the late failure released its slot and was retrieved.
      assert await asyncio.wait_for(workers.run(lambda: "done"), 1) == "done"
      await asyncio.sleep(0)
      assert failures == []
    finally:
      release.set()

  asyncio.run(exercise())
