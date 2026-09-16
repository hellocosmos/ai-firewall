# TrapDefense — AI Firewall for Agents

[![Community verification](https://github.com/hellocosmos/ai-firewall/actions/workflows/test.yml/badge.svg)](https://github.com/hellocosmos/ai-firewall/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-2563EB.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-0F172A.svg)](pyproject.toml)

[English](README.md) · [한국어](README.ko.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md)

**Control AI actions. Protect your data.**

TrapDefense Community is a self-hosted AI Firewall with a local operations UI. Inspect supported HTTP and MCP tool calls, enforce action policy, redact sensitive data and keep decision evidence. The earlier SDK remains in [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security).

```text
AI agents → TrapDefense AI Firewall → Tools / MCP servers / APIs
            Action policy · Data protection · Audit
          ← Inspected responses ←
```

Logical product flow. See [deployment architecture](docs/en/architecture.md) for trusted forwarding, transport visibility and routing requirements.

Community includes single-tenant Microsoft Entra ID console SSO with Administrator and Viewer roles. Console authentication does not authorize agent actions; delegation and approval remain Enterprise features. [Entra SSO](docs/en/identity.md).

## See it in action

<table>
  <tr>
    <td width="58%"><img src="docs/assets/community-dashboard.png" alt="TrapDefense Community dashboard with synthetic allow, block and redact decisions"></td>
    <td width="42%"><img src="docs/assets/entra-sign-in.png" alt="TrapDefense Community sign-in with synthetic Entra and local administrator options"></td>
  </tr>
  <tr>
    <td><strong>Runtime decisions</strong><br>Sanitized synthetic evidence for allow, block and redact outcomes.</td>
    <td><strong>Console identity</strong><br>Local sign-in and a protocol-realistic synthetic Entra flow.</td>
  </tr>
</table>

Screens show the local synthetic demo. They are not evidence of a production Entra tenant or customer traffic deployment.

## Install and open the console

Requires Python 3.11+, Node.js 22.12+ (or 24), npm and local Docker Engine/Desktop. Source installation; no PyPI release is implied.

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall
./scripts/install-console.sh
./scripts/run-console.sh
```

Open [http://127.0.0.1:5176](http://127.0.0.1:5176). Sign in with `admin` / `1234`, then change the password in Settings. English is the default. Use the language selector before or after login; the browser remembers your choice.

## What you can operate

Dashboard and request evidence; local allow/block and PII policy; synthetic HTTP scenarios; audit; password change; interface inventory, listener/upstream settings and verified apply/rollback of the owned Envoy container.

The synthetic requests traverse a real Envoy → gRPC inspector → HTTP destination path. The console records downstream receipts and response redaction; it does not substitute a direct engine call. The default listener is `127.0.0.1:18082`; the inspector uses `18081` and the synthetic destination `18090`.

## Scope and editions

Community includes local policy, explicit HTTP/MCP mappings, trusted-hop signatures, bounded response/SSE inspection and sanitized local evidence. Enterprise Access Broker implementation is separately distributed; Community console SSO does not confer agent identity, delegated access or approvals.

NIC inventory and topology explanation are included. The loopback demo does not configure OS addresses, two-NIC routing, transparent bridges or physical egress. Inline inspection failures block. Console Mirror observes its synchronous path; the separate mirror collector cannot block original traffic.

## Documentation and verification

[Console guide](docs/en/console.md) · [Architecture](docs/en/architecture.md) · [Community / Enterprise](docs/en/editions.md) · [SDK → Proxy](docs/en/migration.md) · [Security](docs/en/security.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

English application source and six complete UI dictionaries are maintained together. Non-English security test fixtures intentionally exercise international input. Localized guides have a language switch at the top.

```bash
.venv/bin/python -m pytest -q
npm run check --prefix console
npm run build --prefix console
# Stop the running console before this Docker test.
TD_CONSOLE_E2E=1 .venv/bin/python -m pytest tests/test_console.py -q
```

These are synthetic local checks, not certification of customer TLS/IdP integration, production enforced routing, HA or performance. Detection has false positives/negatives; local audit is not immutable.

## License

MIT for Community. Private Enterprise code and customer assets are not included.
