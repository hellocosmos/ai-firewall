# Migration from the earlier SDK

[English](../en/migration.md) · [한국어](../ko/migration.md) · [简体中文](../zh-CN/migration.md) · [日本語](../ja/migration.md) · [Español](../es/migration.md) · [Français](../fr/migration.md)

The earlier embedded Python SDK and its history remain at [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security). This repository is the open-source proxy product. SDK compatibility or automatic package migration is not implied.

1. Inventory the HTTP/MCP calls and destinations to protect.
2. Establish a trusted signing adapter after TLS decryption and enforce routing through the proxy.
3. Configure explicit tool/action mappings, limits and redaction fields.
4. Run synthetic observation, then verify inline allow, redact, block and failure behavior.
5. Enable the built-in Access Broker only after configuring verified JWT identity claims, registry records and delegations.

Existing SDK users can retain pinned versions while evaluating a separately routed pilot. Start with the [console guide](console.md). Source installation does not imply a PyPI release or an upgrade of customer deployments. Back up state before changing versions; do not copy synthetic credentials or signing keys into production.

## 0.38 to 0.39 configuration

Version 0.39 intentionally rejects the old `edition` key. Remove it and set `access_broker_enabled: false` for gateway-only inspector configuration or `true` for the built-in broker. The self-hosted profile uses `access_broker.enabled` plus `access_broker.tenant_id` and requires `gateway_auth.mode: jwt` with `gateway_auth.identity_claims`. Replace the `trapdefense-community` package/image name with `trapdefense-ai-firewall`. Back up the broker JSON file and console state before upgrading.
