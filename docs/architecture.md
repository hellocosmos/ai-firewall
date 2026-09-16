# Deployment and trust boundary

```text
Agent → TLS decryptor → trusted forwarding adapter → Envoy → configured upstream
                                                    ↕
                                             TrapDefense inspector
                                                    ↕ (Enterprise only)
                                                Access Broker
```

## Deployment contract

1. Enforce routing outside TrapDefense so protected traffic cannot bypass the proxy.
2. Terminate TLS using your existing authorized infrastructure. The included demo does not decrypt production TLS.
3. At the trusted hop, remove client-supplied `x-td-*` and `x-asr-*` context, reconstruct the request from what that hop actually observed, and attach a signed `x-td-attestation` envelope. Preserve method, authority, path/query, relevant application headers and full body. `identity.py` defines the canonical binding and transport-header exclusions.
4. Keep the shared HMAC key only on that hop and the inspector. It is not an agent API key. Configure a distinct, allowlisted `source_id` for Community. Restrict all plaintext and ExtProc links to an isolated trusted network; no public listener is authenticated by the supplied examples.
5. Envoy applies ExtProc to the request and response. Inline uses `failure_mode_allow: false`, full buffering, size/time limits, and an explicitly configured destination. The attestation is stripped before forwarding.
6. Community maps the request to a configured tool/resource/action and applies local policy. It does not authenticate an end user or establish delegated agent authority.
7. In Enterprise, the private authorizer additionally validates the signed identity/delegation context against the Broker. Existing configs default to Enterprise so upgrading cannot silently remove authorization. Missing Enterprise provider stops startup.

Signing before request redaction binds the original request. A durable local nonce store rejects reuse; a mirror copy checks evidence without consuming an inline nonce or approval. Review `identity.py`, `protocol.py`, and their tests when implementing an adapter. There is no universal drop-in adapter for arbitrary TLS appliances.

## Supported inspection boundary

HTTP requests must match exact configured authority, method and path, with the expected headers. MCP inspection supports the mapped JSON-RPC tool-call shape; protocol versions allowed by a route are configurable. The allowlist is a parser policy, not certification of every MCP protocol feature. Arbitrary MCP transports, WebSocket tunnels, opaque encrypted bodies, unrestricted CONNECT routing and automatic traffic discovery are outside this release.

PII redaction changes only permitted fields or supported response formats; unsafe transformations fail closed. Signature checks provide bounded known-pattern detection, not a semantic guarantee against prompt injection. SSE inspection buffers a complete bounded stream; it is not unbounded, token-by-token streaming.

## Observation and evidence

Mirror mode receives a copy. It cannot block or modify the original request. Headers-only copies have incomplete coverage. Local JSONL records sanitized decisions and evidence; raw content and keys are omitted. Local audit files are not immutable storage or a centralized compliance service.

## Example runtimes

Envoy is the default data plane. `deploy/compose.yaml` is a Docker Desktop local demo, with fixed synthetic destination ports. Linux requires an explicit reachable isolated-network binding for host services; loopback-only demo services are not exposed to a bridged Linux container. Do not expose the unprotected demo upstream publicly.

Optional agentgateway configurations and pinned runtime transport tests are compatibility fixtures. They do not turn the inspector into a managed gateway product. The optional runtime suite currently targets macOS with Docker Desktop and a checksum-pinned agentgateway ARM64 binary. Unit tests run on Python 3.11 and 3.12 in CI.
