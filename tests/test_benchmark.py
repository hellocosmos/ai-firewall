from __future__ import annotations

import asyncio
from argparse import Namespace

import pytest

from asr_proxy.console.benchmark import collect, percentile, summarize, validate


def test_percentiles_and_summary_are_deterministic():
  values = [1, 2, 3, 4, 5]
  assert percentile(values, 0.50) == 3
  assert percentile(values, 0.95) == pytest.approx(4.8)
  assert summarize(values, 2.5) == {
    "count": 5, "min_ms": 1, "p50_ms": 3, "p95_ms": 4.8,
    "max_ms": 5, "mean_ms": 3, "sequential_requests_per_second": 2,
  }


@pytest.mark.parametrize("iterations,warmup", [(4, 0), (501, 0), (5, -1), (5, 51)])
def test_unsafe_run_sizes_are_rejected(iterations, warmup):
  with pytest.raises(ValueError):
    validate(Namespace(iterations=iterations, warmup=warmup))


def test_collect_uses_proxy_evidence_without_captured_content():
  class Runtime:
    def __init__(self):
      self.calls = 0
    def run(self, scenario):
      self.calls += 1
      assert scenario == "read"
      return {"action": "allow", "transport": {"round_trip_ms": 2.5, "http_status": 200}}

  runtime = Runtime()
  samples, elapsed, outcomes = asyncio.run(collect(
    runtime, scenario="read", warmup=2, iterations=5,
  ))
  assert runtime.calls == 7 and samples == [2.5] * 5 and elapsed >= 0
  assert outcomes == {"decisions": {"allow": 5}, "http_statuses": {"200": 5}}
  assert "message" not in str(outcomes)
