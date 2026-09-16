# Community and Enterprise

[English](../en/editions.md) · [한국어](../ko/editions.md) · [简体中文](../zh-CN/editions.md) · [日本語](../ja/editions.md) · [Español](../es/editions.md) · [Français](../fr/editions.md)

## Deployment fit and availability

Self-hosted Community is available as a source-based preview with Docker-backed proxy examples. A unified Docker installation package is planned. TrapDefense Cloud is planned, not available for sign-up: the intended managed offering uses the same inspection foundation.

[Delivery and compatibility](deployment-fit.md)

Community includes single-tenant Microsoft Entra ID console SSO with Administrator and Viewer roles. Console authentication does not authorize agent actions; delegation and approval remain Enterprise features. [Entra SSO](identity.md).

## Current delivery status

| Boundary | Status | Evidence and limit |
|---|---|---|
| Community runtime and console | **Public Community Preview** | Shipped in this MIT repository; CI and synthetic Envoy-path verification pass. Production traffic and capacity remain customer-specific validation. |
| Enterprise Access Broker | **Private pilot implementation** | Separately distributed provider and approval workflow exist; they are not in this repository or presented as general availability. Real IAM, customer policy and failure-path validation are required. |
| Central fleet, distributed HA, immutable audit and hosted service | **Roadmap** | Not shipped or represented by the Community screens. |

Edition names describe product and licensing boundaries, not a claim that every Enterprise roadmap item is generally available.

Community is the MIT-licensed proxy runtime and local operations console in this repository. It includes signed trusted-hop verification, explicit HTTP/MCP mappings, local policy, signature checks, PII redaction, bounded response/SSE inspection, sanitized audit evidence, local login/password changes and proxy settings. No private package or external model API is required.

The separately distributed Enterprise pilot implementation adds the Access Broker: user/agent/task delegation, access decisions and one-time, expiring, request-bound human approval. Existing IAM context must come from a trusted integration; real customer IdP validation remains necessary. The Community UI identifies these unavailable capabilities.

The private provider connects through the `trapdefense.authorizers` / `enterprise` Python entry point. `authorize(request)` enforces decisions; `evaluate(request)` provides non-mutating mirror assessment. Selecting Enterprise without its provider fails startup. Broker token records are scoped decision evidence, not general-purpose OAuth access tokens.

Central fleet management, distributed HA, hosted billing and immutable audit storage are not shipped features. Commercial scope can include the private provider, deployment, policy integration and support; pricing and support terms are separate. Local SQLite and JSONL storage remain mutable.
