# Deployment fit and availability

[English](../en/deployment-fit.md) · [한국어](../ko/deployment-fit.md) · [简体中文](../zh-CN/deployment-fit.md) · [日本語](../ja/deployment-fit.md) · [Español](../es/deployment-fit.md) · [Français](../fr/deployment-fit.md)

Protect the HTTP API and remote MCP calls you can route through a supported inspection path. Keep existing service authentication in your MCP servers and connectors; do not replace your IAM.

Self-hosted Community is available as a source-based preview with Docker-backed proxy examples. A unified Docker installation package is planned. TrapDefense Cloud is planned, not available for sign-up: the intended managed offering uses the same inspection foundation.

You must control a client endpoint, server ingress or a compatible inspected network path. Gateway reachability and bypass prevention are deployment requirements. Closed SaaS-internal calls, local stdio, shell, filesystem and direct database operations are outside this HTTP proxy boundary.

The 0.35 local pilot verifies stateless Streamable HTTP with JSON responses. Bounded SSE inspection is not certification of every streaming MCP server. OAuth, stateful sessions and each customer identity path require compatibility validation. Console Entra SSO is not Agent IAM or downstream authorization.

[Architecture](architecture.md) · [Delivery status](editions.md) · [MCP pilot](mcp-pilot.md)
