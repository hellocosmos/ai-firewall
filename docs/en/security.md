# Security scope and reporting

[English](../en/security.md) · [한국어](../ko/security.md) · [简体中文](../zh-CN/security.md) · [日本語](../ja/security.md) · [Español](../es/security.md) · [Français](../fr/security.md)

Report suspected vulnerabilities privately to **hellocosmos@gmail.com**, including revision, synthetic reproduction and impact. Never put customer data, tokens or live credentials in public issues. No fixed response SLA is promised.

The boundary covers explicitly routed, supported HTTP/MCP traffic from a trusted signed forwarding hop. Local examples are synthetic demonstrations, not hardened appliances.

- Restrict plaintext, ExtProc and mirror listeners to trusted networks and senders.
- Protect and rotate signing keys; never give them to agents. Enforce upstream routing against bypass.
- Inline inspector or authorization failures must fail closed. The separate mirror collector cannot block originals; console Mirror uses a synchronous path and still blocks on inspector transport failure.
- Configure body/time limits, mappings and field redaction. Buffered SSE is bounded, not unbounded streaming.
- Local SQLite replay protection and audit storage do not establish distributed HA or immutable retention.
- Signature and PII detection can produce false positives and false negatives.
- A signed source does not establish human or agent identity. Enterprise needs a separately trusted identity chain.

The console seeds a local `admin` account with password `1234`; change it in Settings. Management binds to loopback. Network settings manage the owned demo Envoy container, not OS interface addresses, physical routing or firewall rules. Authentication, CSRF checks and hashed passwords do not make the synthetic demo a production IAM deployment. MIT covers Community code; private implementation and customer assets are excluded.
