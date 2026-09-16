# Security scope and reporting

Report suspected vulnerabilities privately to **hellocosmos@gmail.com** with the affected revision, synthetic reproduction and impact. Do not include customer data, tokens or live credentials in public issues. This project does not promise a fixed response SLA.

The protected boundary is explicitly routed, supported HTTP/MCP traffic delivered by a trusted, signed forwarding hop. The examples are local synthetic demonstrations, not hardened production appliance configurations.

- Restrict plaintext, ExtProc and mirror listeners to the intended network and trusted senders.
- Protect and rotate hop keys through your deployment secret management; never hand them to agents.
- Enforce routing and upstream access so agents cannot bypass this boundary.
- Inline inspection and Enterprise provider failures must not fail open. Mirror is observation only.
- Configure body/time limits, mappings and field-level redaction before connecting real workloads.
- Local SQLite replay protection and JSONL evidence do not establish distributed HA or immutable retention.
- Known-pattern detection and recognizer-based PII detection have false positives and false negatives.
- A signed source is not proof of an end-user identity. Enterprise requires a separately trusted identity chain.

No SDK, internal strategy, customer artifacts or private Enterprise implementation is released here. MIT license terms apply to the Community code; commercial support is separate.
