# TrapDefense — AI Firewall for Agents

[한국어](README.ko.md) · [Website](https://trapdefense.com) · [Architecture](docs/architecture.md) · [Editions](docs/editions.md)

**Inspect and control supported HTTP and MCP actions after TLS decryption.**

TrapDefense Community is a self-hosted proxy inspection runtime. Route decrypted traffic through Envoy and the TrapDefense inspector to apply local policy, block unsafe requests, redact sensitive content, and record sanitized decision evidence.

```text
AI agent → existing TLS decryptor → trusted forwarding adapter
                                      ↓
                           Envoy + TrapDefense inspector
                                      ↓
                              configured destination
                         ← response inspection ←
```

This repository contains the **Community proxy product**, not an application SDK. The previous SDK remains at [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security).

## Community capabilities

- Explicit HTTP route and MCP tool/action mappings; unmapped inline requests fail closed.
- Local allow/block policy, egress checks, bounded signature detection, and Presidio PII redaction.
- Complete buffered request/response inspection, including supported SSE formats.
- Signed trusted-hop context bound to the request, with expiry and replay rejection.
- Sanitized local JSONL audit evidence. Mirror mode observes copies and never blocks original traffic.
- No Enterprise package, license server, or external model API required.

## Run the local demo

Python 3.11+ and Docker Desktop are required for the Envoy demonstration. Commands below use the repository source; no PyPI release is implied.

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
trapdefense-demo init --state-dir .runtime-state/demo
```

Start the following in three terminals from the same directory:

```bash
# Terminal 1: Community inspector
. .venv/bin/activate
trapdefense-inspector --config .runtime-state/demo/inspector.yaml \
  --key-file .runtime-state/demo/attestation.key --grpc-host 0.0.0.0

# Terminal 2: synthetic destination
. .venv/bin/activate
trapdefense-demo upstream

# Terminal 3: Envoy data plane, published on loopback only
docker compose -f deploy/compose.yaml up
```

Then simulate the trusted forwarding adapter with synthetic requests:

```bash
trapdefense-demo send --state-dir .runtime-state/demo --endpoint http://127.0.0.1:18082
trapdefense-demo send --state-dir .runtime-state/demo --endpoint http://127.0.0.1:18082 \
  --message 'Email alex@example.com'
trapdefense-demo send --state-dir .runtime-state/demo --endpoint http://127.0.0.1:18082 --tool delete
```

Expect allow (200), redacted upstream content (200), and deny (403). The demo destination performs no real business action. Stop Compose and the two local processes after use.

The local ExtProc listener is exposed to Docker for this demo only. Restrict it to the proxy network in deployment; it is not an authenticated public gRPC endpoint.

## Deploy behind a TLS decryptor

TLS termination alone is insufficient. Your decryptor or a trusted adapter must preserve HTTP method, authority, path/query, application headers and complete body, remove client-supplied forwarding context, and sign the observed request. The signing key belongs only to that hop. Community proves the trusted source, **not the human or agent identity**. See the [integration contract](docs/architecture.md).

Envoy routes to explicitly configured upstreams. This is not an unrestricted CONNECT proxy, packet sniffer, automatic TLS decryptor, or arbitrary MCP transport implementation. Example routing targets a loopback synthetic upstream, not production destinations.

## Community and Enterprise

Community protects a configured proxy boundary with local policy. Enterprise adds the separately distributed Access Broker for user/agent/task delegation and approval. It connects through a public authorization extension contract. Selecting Enterprise without its provider fails startup; there is no silent downgrade.

Central fleet management, HA, managed services and immutable audit storage are roadmap capabilities, not claims about this Community release. [Edition details](docs/editions.md)

## Verification and limits

```bash
pytest -q
# Optional macOS / Docker Desktop transport + local TLS simulation
sh deploy/inspection/fetch-runtimes.sh
TD_RUNTIME_SMOKE=1 pytest tests/runtime -q
```

Local TLS tests use temporary test certificates and synthetic traffic. They do not certify customer TLS appliances, production forced routing, real IdP integration or performance/HA. Buffered SSE has body/time limits and does not provide unbounded live streaming. Signature detection is not complete prompt-injection prevention. [Security scope](SECURITY.md)

## License

MIT. Enterprise implementation and internal operating assets are not included in this repository.
