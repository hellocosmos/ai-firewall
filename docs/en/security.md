# Security scope and reporting

[English](../en/security.md) · [한국어](../ko/security.md) · [简体中文](../zh-CN/security.md) · [日本語](../ja/security.md) · [Español](../es/security.md) · [Français](../fr/security.md)

Community includes single-tenant Microsoft Entra ID console SSO with Administrator and Viewer roles. Console authentication does not authorize agent actions; delegation and approval remain Enterprise features. [Entra SSO](identity.md).

Report suspected vulnerabilities privately to **hellocosmos@gmail.com** , including revision, synthetic reproduction and impact. Never put customer data, tokens or live credentials in public issues. No fixed response SLA is promised.

## PII coverage

Offline inspection evaluates all six language profiles for every supported payload:

- English: email, phone, credit card, IBAN and US SSN.
- Korean: resident and foreigner registration, driver licence, passport and business registration numbers.
- Simplified Chinese: phone and GB 11643 resident identity numbers.
- Japanese: phone and 12-digit Individual Numbers (My Number).
- Spanish: phone, NIF, NIE and passport numbers.
- French: phone and NIR social security numbers, including Corsica department codes.

National identifiers use format and checksum validation where the standard defines one. The implementations follow [China GB 11643](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=080D6FBF2BB468F9007657F26D60013E), the [Japanese Individual Number modulus-11 rule](https://www.j-lis.go.jp/data/open/cnt/3/1282/1/H2707_qa.pdf) and the [INSEE NIR control key](https://xml.insee.fr/schema/nir.html). This is deterministic pattern inspection, not general NER: names, locations, postal addresses, images, OCR and arbitrary files are outside this release.

## Secret exposure coverage

Offline inspection blocks recognized private keys, common AWS, GitHub, GCP, Slack, Stripe and OpenAI token forms, structurally valid signed JWTs, Azure Storage SAS query combinations, and high-entropy values in sensitive JSON fields. It applies to supported request bodies, responses and reassembled SSE streams.

Request `Authorization`, cookie and API-key headers are preserved only for the already attested, explicitly mapped destination path and are omitted from audit evidence. Response headers are inspected. Malformed JWT-like text, ordinary `sig` parameters and documented placeholders do not block. A detection records only `secret_detected`, never the captured value. This deterministic coverage can miss new or custom formats and can produce false positives; rotate any real credential that may have crossed an untrusted boundary.

The boundary covers explicitly routed, supported HTTP/MCP traffic from a trusted signed forwarding hop. Local examples are synthetic demonstrations, not hardened appliances.

- Restrict plaintext, ExtProc and mirror listeners to trusted networks and senders.
- Protect and rotate signing keys; never give them to agents. Enforce upstream routing against bypass.
- Inline inspector or authorization failures must fail closed. The separate mirror collector cannot block originals; console Mirror uses a synchronous path and still blocks on inspector transport failure.
- Configure body/time limits, mappings and field redaction. Buffered SSE is bounded, not unbounded streaming.
- Local SQLite replay protection and audit storage do not establish distributed HA or immutable retention.
- Signature and PII detection can produce false positives and false negatives.
- A signed source does not establish human or agent identity. Enterprise needs a separately trusted identity chain.

The console seeds a local `admin` account with password `1234`; change it in Settings. Management binds to loopback. Network settings manage the owned demo Envoy container, not OS interface addresses, physical routing or firewall rules. Authentication, CSRF checks and hashed passwords do not make the synthetic demo a production IAM deployment. MIT covers Community code; private implementation and customer assets are excluded.
