# Changelog

All notable changes to TrapDefense Community are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Community source releases use the `0.31`, `0.32` numbering sequence.

## [0.32] - 2026-09-16

### Added

- Bounded offline detection for recognized AWS, GitHub, GCP, Slack, Stripe and OpenAI token forms.
- Structural signed-JWT validation, Azure Storage SAS query detection and high-entropy credential checks for sensitive JSON fields.
- Secret inspection across supported request bodies, responses, headers and reassembled SSE streams.
- A six-language `Block leaked credential` console scenario that traverses the installed Envoy path.

### Security

- Recognized credentials fail closed with the stable `secret_detected` reason and captured values are never copied into verdict evidence or audit records.
- Request authorization, cookie and API-key headers remain pass-through only on the signed, explicitly mapped destination path; response headers are inspected.
- Malformed JWT-like strings, ordinary `sig` query parameters and documented placeholders are excluded to reduce obvious false positives.

### Verified

- Synthetic provider-token, JWT, Azure SAS, sensitive-field, request, response, SSE split-stream, credential-header and sanitized-evidence tests.
- Existing Community request, response, PII, protocol, console and proxy integration suites.

## [0.31] - 2026-09-16

### Added

- Offline PII profiles for English, Korean, Simplified Chinese, Japanese, Spanish and French.
- Checksum-validated Chinese GB 11643 resident IDs, Japanese Individual Numbers and French NIR social security numbers.
- Presidio Spanish NIF, NIE and passport recognition.
- Region-aware phone recognition for Chinese, Japanese, Spanish and French inputs.

### Security

- National identifier patterns reject invalid dates or check digits instead of accepting format-only matches.
- All six language profiles run for every supported payload, so the configured UI language does not change enforcement.
- Inspection remains deterministic and offline. Names, locations, addresses, images, OCR and general NER are explicitly outside this release.

### Verified

- Locale-specific positive, invalid-checksum, redaction, timeout and no-network tests.
- Existing request, response, SSE and fail-closed inspection suites.

## [0.3.0] - 2026-09-16

### Added

- Self-hosted Community AI Firewall with Envoy ExtProc request and response inspection.
- A local operations console for dashboard, event, policy, connection, audit and settings workflows.
- Explicit HTTP and MCP action mappings, local allow/block rules, PII block or redaction, trusted-hop signatures and replay protection.
- Sanitized local decision evidence and synthetic HTTP scenarios that traverse the proxy path.
- Single-tenant Microsoft Entra ID console SSO with Administrator and Viewer app roles, plus a protocol-realistic synthetic Entra flow for local evaluation.
- English, Korean, Simplified Chinese, Japanese, Spanish and French console dictionaries and guides.

### Security

- Inline inspection fails closed when complete policy evaluation cannot finish.
- Console writes require same-origin requests and a CSRF header, and local login attempts are rate limited.
- Community source verification remains distinct from Enterprise agent identity verification and delegated authorization.

### Verified

- Community tests run on Python 3.11 and 3.12 in GitHub Actions.
- Console type checks and production build run on Node.js 22 in GitHub Actions.
- Linux CI runs the Envoy to gRPC inspector to synthetic HTTP destination integration test.

### Known boundaries

- This is a source installation; no PyPI package is implied.
- The included screens and scenarios use synthetic data.
- A real Entra tenant, customer TLS path, enforced production routing, high availability and performance are not certified by this release.
- Local audit storage is mutable, and content detection can produce false positives or false negatives.
- Enterprise Access Broker, approvals and delegated authorization are distributed separately.

[0.32]: https://github.com/hellocosmos/ai-firewall/releases/tag/v0.32
[0.31]: https://github.com/hellocosmos/ai-firewall/releases/tag/v0.31
[0.3.0]: https://github.com/hellocosmos/ai-firewall/releases/tag/v0.3.0
