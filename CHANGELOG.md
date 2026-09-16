# Changelog

All notable changes to TrapDefense Community are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Community source releases use the `0.31`, `0.32`, `0.33`, `0.34` numbering sequence.

## [Unreleased]

## [0.36] - 2026-09-17

### Docker self-hosting preview

- Source-built Compose package: authenticated signing adapter, private Envoy/inspector and persistent operations console. No host Docker socket.
- Explicit fixed-destination JSON HTTP/stateless JSON MCP contract; separate deployment key and destination Bearer/API Key credentials, optional static bearer file.
- Initial administrator password, persistent keys/policies/events, explicit mapping reset, HTTPS upstream validation and fail-closed forwarding.
- Deployment-aware UI and six-language installation/integration guides. Existing synthetic demo remains available separately.
- No claim of Cloud availability, universal OAuth/MCP compatibility, customer IAM validation, long-lived SSE support or HA.

## [0.35] - 2026-09-17

### Added

- Optional real MCP pilot using the pinned official Python SDK: initialization, discovery and persisted document tool operations through the existing Envoy/Community inspector.
- Separate local signing adapter with fixed destination, private key, fresh attestations, reserved-context removal and bounded forwarding; no agent SDK or production network-isolation claim.
- Deterministic request/response PII and secret checks, denied deletion with downstream state verification, unknown/unsigned calls and inspector-outage blocking.
- Bounded actual local LLM tool loop with schema validation, explicit model endpoint, no scripted fallback, no identical-call replay and sanitized model/protocol evidence.
- Six-language guides, direct-versus-proxy sequential latency measurements and an opt-in CI regression.

### Documentation

- Clarify supported HTTP/MCP deployment paths, existing authentication, self-hosted availability and planned Docker packaging / managed Cloud across six languages.

### Limits

- A semantic malicious instruction outside the current signatures passes unchanged. The pilot records this known detection miss separately from policy enforcement.
- Model refusal, incomplete tasks and unexercised cases are distinguished from firewall detection. Response blocking cannot undo an already-executed tool action.
- Stateless Streamable HTTP JSON and finite synthetic documents only; no customer MCP/OAuth, production sizing, HA or language migration claim.


## [0.34] - 2026-09-16

### Operations

- Same-host 1/2/4 inspector supervision, active Envoy health checks and bounded process recovery.
- Console worker status and administrator apply/start/stop controls, with shared versioned policies and sanitized events.
- New streams read the committed policy; in-flight streams retain the request policy snapshot.
- Opt-in Linux systemd user-service installer and removal commands. Host boot/linger validation remains deployment-specific.
- Six-language operation guides. Cross-server HA remains unimplemented.

### Verified

- Ubuntu 26.04 lab installation: 369 unit tests, 10 console tests and 6 real Envoy/pool tests passed; 31 opt-in tests were skipped in the default suite.
- Real host reboot with linger: automatic startup before SSH login, two healthy inspectors, persisted policy/events and synthetic allow/block/redaction traffic.
- Browser verification of inspector controls and English/Korean rendering; desktop/mobile landing operations layout checked.
- Runtime pool tests now use the native Docker context on Linux instead of requiring Docker Desktop.

### Performance and security

- Equivalent ASCII candidate prefilters for fixed PII/signature patterns, native control-character cleanup and indexed nonce expiry.
- Shared local replay state across workers; no automatic tool-call retry. Exhausted worker recovery stops the pool.
- Process scaling changes briefly interrupt the proxy; failed changes attempt rollback, with unavailable inspection failing closed.


### Added

- A bounded `trapdefense-benchmark` command for repeatable sequential measurements through the local Envoy, gRPC inspector and synthetic destination path.
- Community Preview maturity labels, five-minute evaluation success criteria and explicit shipped/private/roadmap edition status.

## [0.33] - 2026-09-16

### Added

- Deterministic PII policy overrides for HTTP/MCP routes and mapped actions or MCP tools, with tool/action → route → global precedence.
- Request-selected PII policy propagation into supported JSON, text and complete buffered SSE responses.
- Console controls for per-tool inherit, redact or block behavior and sanitized evidence of the selected policy scope.

### Security

- Mirror keeps original request and response bytes unchanged while complete detections retain explicit `would_redact` or `would_block` assessments.
- Incomplete capture, unsupported inspection and transport failures remain `unknown`; policy evidence never stores inspected content.
- Existing configurations inherit the global PII action unless an explicit route or tool override is present.

### Verified

- Synthetic tool, route and global precedence tests for request and response inspection.
- Six matching UI dictionaries and localized console/security guidance.
- Community proxy integration covers a tool-specific block policy in Mirror mode without enforcement or request mutation.

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

[0.33]: https://github.com/hellocosmos/ai-firewall/releases/tag/v0.33
[0.32]: https://github.com/hellocosmos/ai-firewall/releases/tag/v0.32
[0.31]: https://github.com/hellocosmos/ai-firewall/releases/tag/v0.31
[0.3.0]: https://github.com/hellocosmos/ai-firewall/releases/tag/v0.3.0
