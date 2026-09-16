# Architecture and trust boundary

[English](../en/architecture.md) · [한국어](../ko/architecture.md) · [简体中文](../zh-CN/architecture.md) · [日本語](../ja/architecture.md) · [Español](../es/architecture.md) · [Français](../fr/architecture.md)

```text
AI agents → TrapDefense AI Firewall → Tools / MCP servers / APIs
            Action policy · Data protection · Audit
          ← Inspected responses ←
```

## Data plane and control plane

The console's management API authenticates a local operator, persists policy and serves the UI. Envoy forwards supported HTTP/MCP traffic and calls the inspector through gRPC ExtProc for request and response inspection. Each stream snapshots its policy. A synthetic no-op HTTP destination provides receipt evidence. The console is installed with [these instructions](console.md).

## Trust contract

1. Enforce routing outside TrapDefense so protected traffic cannot bypass the proxy.
2. Use an authorized existing TLS decryptor. The demo does not decrypt production TLS.
3. A trusted adapter removes client-supplied `x-td-*` and `x-asr-*` context and signs what it observed. Preserve method, authority, path/query, application headers and complete body. `inspection/identity.py` defines canonical binding and exclusions.
4. Keep the HMAC key only on the trusted hop and inspector; never distribute it to agents. Allowlist the Community `source_id`. Isolate plaintext and ExtProc links: these examples do not authenticate a public gRPC listener.
5. Envoy uses complete buffered inspection, bounded size/time and `failure_mode_allow: false`. It removes the attestation before forwarding. Signing binds the original request; durable approval, when present, binds the post-redaction action digest.
6. Community applies explicit local route/tool/resource/action rules and verifies a forwarding source. It does not establish a user identity or delegated agent authority.
7. Enterprise additionally validates identity/delegation through a separate private provider. Legacy configs default to Enterprise; a missing provider stops startup rather than silently downgrading.

There is no universal adapter for arbitrary TLS appliances. Integrations must prevent metadata spoofing and enforce upstream access restrictions.

## Supported boundary and limits

Routes match exact authority, method, path and expected headers. MCP support covers explicitly mapped JSON-RPC calls and configured protocol versions; this is not certification of every MCP feature. Arbitrary MCP transports, WebSocket tunnels, encrypted opaque bodies, unrestricted CONNECT and automatic traffic discovery are outside this release. Redaction only modifies allowed fields/formats and unsafe transformations fail closed. Signatures detect bounded known patterns; they do not guarantee prevention of every prompt injection. SSE buffers a complete bounded stream, not unbounded token-by-token output.

The separate mirror collector receives copies and cannot block or change originals; headers-only copies are incomplete. The console's Mirror setting instead observes its synchronous proxy path without changing the body; inspector transport failure still blocks. Both must be distinguished in deployment and reporting. JSONL inspector evidence and SQLite console audit omit original content/keys but are editable local storage, not immutable compliance retention.

## Network profile

The console uses loopback and a digest-pinned amd64/arm64 Envoy image. Docker Desktop provides host forwarding on macOS; Linux uses host networking. NIC inventory reports OS interfaces, not physical port count. Dual-NIC routing, transparent bridge, physical egress pinning, real IdP/TLS equipment, HA and production performance remain separate work. Optional agentgateway/runtime fixtures are compatibility tests, not a managed gateway service.
