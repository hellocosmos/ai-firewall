# Migration from the earlier SDK

[English](../en/migration.md) · [한국어](../ko/migration.md) · [简体中文](../zh-CN/migration.md) · [日本語](../ja/migration.md) · [Español](../es/migration.md) · [Français](../fr/migration.md)

The earlier embedded Python SDK and its history remain at [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security). This repository is the new Community proxy product. SDK compatibility or automatic package migration is not implied.

1. Inventory the HTTP/MCP calls and destinations to protect.
2. Establish a trusted signing adapter after TLS decryption and enforce routing through the proxy.
3. Configure explicit tool/action mappings, limits and redaction fields.
4. Run synthetic observation, then verify inline allow, redact, block and failure behavior.
5. Add the private Enterprise provider only when delegated access and request-bound approval are needed.

Existing SDK users can retain pinned versions while evaluating a separately routed pilot. Start with the [console guide](console.md). Source installation does not imply a PyPI release or an upgrade of customer deployments. Back up state before changing versions; do not copy synthetic credentials or signing keys into production.
