# Deployment fit and availability

> **AISG:** [Connect, identify, control, verify](aisg.md). Gateway access uses a deployment key or verified JWT. Local agent_key mode identifies a registered agent without an external IAM. JWT identity_mode: agent uses verified tenant/agent claims; delegated mode additionally requires user, task and delegation. Existing agents require delegation by default.

[English](../en/deployment-fit.md) · [한국어](../ko/deployment-fit.md) · [简体中文](../zh-CN/deployment-fit.md) · [日本語](../ja/deployment-fit.md) · [Español](../es/deployment-fit.md) · [Français](../fr/deployment-fit.md)

Protect the HTTP API and remote MCP calls you can route through a supported inspection path. Keep existing service authentication in your MCP servers and connectors; do not replace your IAM.

Self-hosted TrapDefense 0.42 includes a source-built Docker Compose package with client-key or external-JWT gateway authentication and independent target credentials. TrapDefense Cloud remains planned and is not available for sign-up.

You must control a client endpoint, server ingress or a compatible inspected network path. Gateway reachability and bypass prevention are deployment requirements. Closed SaaS-internal calls, local stdio, shell, filesystem and direct database operations are outside this HTTP proxy boundary.

The current qualification combines a live OpenAI model-to-synthetic-MCP workflow, official provider SDK fixtures, real local MCP/Keycloak paths and VS Code initialization/discovery evidence. Model SSE is buffered; stateful MCP, customer identity policy, cross-host HA and production capacity are not certified. See [0.42 workflow and limits](agent-workflow.md).

[Architecture](architecture.md) · [Delivery status](editions.md) · [MCP pilot](mcp-pilot.md)

[Docker self-hosting](self-hosting.md) · [Gateway client compatibility](gateway-compatibility.md)
