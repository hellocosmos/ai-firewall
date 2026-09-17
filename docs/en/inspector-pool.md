# Same-host inspector pool

[English](../en/inspector-pool.md) · [한국어](../ko/inspector-pool.md) · [简体中文](../zh-CN/inspector-pool.md) · [日本語](../ja/inspector-pool.md) · [Español](../es/inspector-pool.md) · [Français](../fr/inspector-pool.md)

`trapdefense-inspector-pool` supervises **1, 2 or 4 existing inspector processes** and generates their Envoy connection configuration. It does not start Docker, replace the console runtime, change host networking, or implement cross-host HA. The console's process controls do not manage this standalone pool. The built-in file-backed broker is supported for same-host POSIX processes through file locking and atomic snapshots. This is not multi-host HA.

## Start

Install the modified package to register the command, or use `.venv/bin/python -m asr_proxy.inspection.pool` with the same arguments. Stop any installation already using the chosen proxy/upstream ports before following this example. Do not reuse a live console's state directory.

Create **new synthetic state** for an evaluation; `init` refuses to overwrite existing state:

```bash
.venv/bin/trapdefense-demo init --state-dir "$PWD/.runtime-state/pool-demo"
.venv/bin/trapdefense-demo upstream --port 18090
```

In another terminal, start the pool. For a real installation, use its existing policy and trusted-hop key instead of the demo files:

```bash
.venv/bin/trapdefense-inspector-pool \
  --config "$PWD/.runtime-state/pool-demo/inspector.yaml" \
  --key-file "$PWD/.runtime-state/pool-demo/attestation.key" \
  --state-directory "$PWD/.runtime-state/pool-supervisor" \
  --envoy-output "$PWD/.runtime-state/pool-envoy.yaml" \
  --replicas 2
```

Defaults reserve gRPC ports `18101..18104` and health ports `18111..18114` according to the replica count. All children bind loopback. Use `--grpc-base-port`, `--health-base-port`, `--proxy-port`, and `--upstream-port` to avoid collisions. The generated listener defaults to `127.0.0.1:18082`. The upstream address defaults to `127.0.0.1` and must match the mapped destination in your policy.

### Envoy on Linux (host networking)

Wait for `pool-supervisor/status.json` to report `healthy`, then start Envoy separately:

```bash
docker run --rm --name td-pool-envoy --network host \
  --read-only --cap-drop ALL --security-opt no-new-privileges --user 65532:65532 \
  --mount "type=bind,source=$PWD/.runtime-state/pool-envoy.yaml,target=/etc/envoy/pool.yaml,readonly" \
  --entrypoint /usr/local/bin/envoy \
  envoyproxy/envoy@sha256:57e14a549d7bd43c8d3f6d03e8cfa653e037d4b38e133acd9b54f38c524401b4 \
  --concurrency 2 -c /etc/envoy/pool.yaml
```

### Docker Desktop on macOS

Add these arguments to the **pool command** before it starts:

```text
--proxy-bind 0.0.0.0 --inspector-address host.docker.internal --upstream-address host.docker.internal
```

Run the same Envoy command with `--publish 127.0.0.1:18082:18082` **instead of** `--network host`. `0.0.0.0` is the listener inside the container; the published host port remains loopback-only. The generated configuration retains request/response buffering and fail-closed ExtProc behavior. It has no tool-request retry policy.

## Shared state and recovery

- All replicas share the same canonical **local SQLite nonce DB** and locked sanitized audit file. Relative paths in the policy resolve against the supervisor's starting working directory, matching the single-inspector behavior. Never give replicas separate nonce stores or place SQLite on a network filesystem.
- Policy and binary key are snapshotted privately at startup. A restarted child gets the same snapshot. To change policy, rotate the key or change replica count, stop/restart the entire pool and coordinate Envoy configuration reload and trusted-hop signing. There is no hot reload or zero-downtime rollout guarantee.
- `--max-restarts 3` permits three replacements per child over the supervisor lifetime. Backoff is 1, 2, then 4 seconds. Exited or repeatedly unhealthy children are replaced. Exhausted recovery stops the entire pool and exits nonzero; the status stays `failed`.
- Envoy checks each process's health endpoint. Panic routing is disabled. A failed in-flight request can return an error; it is not automatically retried. All-inspector failure must block traffic rather than bypass inspection.
- SIGTERM/Ctrl-C stops the children. Children also monitor their supervisor PID and stop after supervisor death. A force-killed supervisor cannot clean its private snapshot directory or final status. Check the recorded PID, timestamp and live health; an old `healthy` JSON file is not proof of a running pool. Remove abandoned snapshot directories only after confirming their processes have exited.

## Status and limits

`status.json` contains state, supervisor/child PIDs, ports and restart counts; private child logs are `inspector-N.log`. No key or raw request body is written to status. Existing state directories must have mode `0700`; keys must not be group/world-readable. Port conflicts and duplicate supervisors using the same state directory are rejected.

This packaging has local process-lifecycle and real-Envoy security tests. Earlier capacity experiments do not certify this supervisor on customer hardware. Long-duration load, machine failure, external IAM, distributed authorization, large streaming responses, UI integration and service-manager installation require separate validation. Use a service manager with process-group cleanup for production evaluation; that integration is not installed by this command.
