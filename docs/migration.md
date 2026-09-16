# From the earlier SDK repository

`hellocosmos/agent-runtime-security` preserves the earlier embedded Python SDK and its history. It is not renamed or silently converted into a proxy.

`hellocosmos/ai-firewall` is the new Community proxy product. There is no SDK API compatibility claim and no automatic package upgrade path. Existing SDK consumers can keep their pinned version while evaluating a separately routed proxy pilot.

1. Inventory the exact HTTP/MCP calls and destinations to protect.
2. Establish a trusted forwarding adapter after your TLS decryptor and an enforced routing boundary.
3. Configure explicit tool/action mappings and redaction fields.
4. Use mirror assessment with synthetic data, then validate inline allow/redact/block and failure behavior.
5. Add the private Enterprise provider only when delegated authority and request-bound approval are required.

The first public proxy version is source-installable. No PyPI publishing or migration of existing customer deployments is implied.
