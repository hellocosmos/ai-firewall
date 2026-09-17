"""Reproducible synthetic baseline for the installed AI Firewall path."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import statistics
import sys
import tempfile
import time
from importlib.metadata import PackageNotFoundError, version

from .scenarios import CASES


SCENARIOS = ("read", "pii", "secret", "response")


def percentile(values: list[float], percent: float) -> float:
  ordered = sorted(values)
  position = (len(ordered) - 1) * percent
  lower = int(position)
  upper = min(lower + 1, len(ordered) - 1)
  return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize(samples: list[float], elapsed: float) -> dict:
  return {
    "count": len(samples),
    "min_ms": round(min(samples), 2),
    "p50_ms": round(percentile(samples, 0.50), 2),
    "p95_ms": round(percentile(samples, 0.95), 2),
    "max_ms": round(max(samples), 2),
    "mean_ms": round(statistics.fmean(samples), 2),
    "sequential_requests_per_second": round(len(samples) / elapsed, 2),
  }


async def collect(runtime, *, scenario: str, warmup: int, iterations: int) -> tuple[list[float], float, dict]:
  for _ in range(warmup):
    await asyncio.to_thread(runtime.run, scenario)
  samples = []
  decisions, statuses = {}, {}
  started = time.perf_counter()
  for _ in range(iterations):
    event = await asyncio.to_thread(runtime.run, scenario)
    samples.append(float(event["transport"]["round_trip_ms"]))
    action = event["action"]
    status = str(event["transport"]["http_status"])
    decisions[action] = decisions.get(action, 0) + 1
    statuses[status] = statuses.get(status, 0) + 1
  return samples, time.perf_counter() - started, {
    "decisions": decisions, "http_statuses": statuses,
  }


def parser() -> argparse.ArgumentParser:
  value = argparse.ArgumentParser(description=(
    "Measure a synthetic sequential baseline through Envoy, gRPC ExtProc and the local HTTP destination."
  ))
  value.add_argument("--scenario", choices=SCENARIOS, default="read")
  value.add_argument("--iterations", type=int, default=30)
  value.add_argument("--warmup", type=int, default=3)
  return value


def validate(args) -> None:
  if not 5 <= args.iterations <= 500:
    raise ValueError("iterations must be between 5 and 500")
  if not 0 <= args.warmup <= 50:
    raise ValueError("warmup must be between 0 and 50")


async def run(args) -> dict:
  from .runtime import Runtime

  validate(args)
  with tempfile.TemporaryDirectory(prefix="trapdefense-benchmark-") as directory:
    runtime = Runtime(directory)
    try:
      await runtime.start()
      samples, elapsed, outcomes = await collect(runtime, scenario=args.scenario,
        warmup=args.warmup, iterations=args.iterations)
    finally:
      if runtime.grpc_server is not None or runtime.destination is not None:
        await runtime.stop()
  try:
    release = version("trapdefense-ai-firewall")
  except PackageNotFoundError:
    release = "source-checkout"
  return {
    "kind": "synthetic_local_baseline",
    "release": release,
    "inspection_path": "Envoy HTTP -> gRPC ExtProc -> synthetic HTTP destination",
    "scenario": args.scenario,
    "scenario_label": CASES[args.scenario]["label"],
    "warmup": args.warmup,
    "measurements": summarize(samples, elapsed),
    "outcomes": outcomes,
    "environment": {
      "os": platform.system(), "architecture": platform.machine(),
      "python": platform.python_version(), "logical_cpus": os.cpu_count(),
    },
    "limitations": [
      "Sequential synthetic requests on loopback",
      "Includes local Docker, storage and host scheduling effects",
      "Not a production capacity, HA or customer traffic certification",
    ],
  }


def main() -> None:
  args = parser().parse_args()
  try:
    report = asyncio.run(run(args))
  except (RuntimeError, ValueError, OSError) as error:
    print(f"Benchmark failed: {error}", file=sys.stderr)
    raise SystemExit(1) from None
  print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
  main()
