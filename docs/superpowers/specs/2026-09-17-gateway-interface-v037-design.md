# Gateway Interface 0.37 Design

## Purpose

TrapDefense Community 0.37 adds a standards-aligned authentication boundary to the existing fixed-destination HTTP/MCP gateway. The release must let supported clients authenticate to TrapDefense independently from the credential TrapDefense uses for the configured target. It must preserve the 0.36 client-key installation path and continue to fail closed.

This release is a compatibility and trust-boundary release. It does not turn Community into an OAuth authorization server, credential vault, agent IAM, or general-purpose streaming proxy.

## Evidence basis

The interface follows four observed ecosystem patterns:

1. Remote MCP clients connect by replacing the server URL and supplying either a configured key header or an OAuth Bearer token.
2. OAuth-protected MCP endpoints act as resource servers, publish OAuth Protected Resource Metadata, and return a `WWW-Authenticate` challenge on `401`.
3. Gateways model inbound caller authentication separately from outbound target authentication.
4. A token accepted by an MCP resource server must be audience-bound to that resource and must not be replayed unchanged to an unrelated upstream API.

Primary references:

- MCP Authorization Specification 2025-06-18
- RFC 9728 OAuth 2.0 Protected Resource Metadata
- Azure API Management MCP security guidance
- Amazon Bedrock AgentCore inbound and outbound gateway authorization guidance

## Selected approach

TrapDefense will act as an OAuth resource server when JWT gateway authentication is selected. The external identity provider remains responsible for interactive login, client registration, authorization-code flow, token issuance, refresh, Conditional Access, and revocation policy.

The deployment retains one fixed upstream origin. This keeps the current destination-binding and Envoy configuration intact while making the authentication contract extensible. A future multi-target router can reuse the target credential model without weakening this release.

## Configuration contract

`gateway_auth` controls access from the client to TrapDefense.

### Client-key mode

```yaml
gateway_auth:
  mode: client_key
```

The client supplies `X-TD-Client-Key`. This is the default and preserves 0.36 behavior.

### JWT mode

```yaml
gateway_auth:
  mode: jwt
  issuer: https://login.example.com/tenant/v2.0
  audience: https://firewall.example.com/mcp
  jwks_uri: https://login.example.com/tenant/discovery/v2.0/keys
  resource: https://firewall.example.com/mcp
  authorization_servers:
    - https://login.example.com/tenant/v2.0
  required_scopes: [mcp.invoke]
```

JWT mode accepts only `Authorization: Bearer`. It validates RS256 signature, issuer, audience, expiry, issued-at time, subject, and configured scopes using the configured JWKS endpoint. JWKS and metadata URLs require HTTPS except for an explicitly enabled loopback-only synthetic test setting. Validation failure returns a sanitized `401`; a valid token missing scope returns `403`.

JWT mode publishes the RFC 9728 path derived from the resource URI. For `https://firewall.example.com/mcp`, that path is `/.well-known/oauth-protected-resource/mcp`. The metadata identifies the configured resource and authorization servers. Its `WWW-Authenticate` challenge contains the derived absolute metadata URL.

`target_auth` controls the independent credential sent from TrapDefense to the fixed target.

```yaml
target_auth:
  mode: static_api_key
  secret_file: /state/target-api-key
  header: Ocp-Apim-Subscription-Key
  prefix: ""
```

Supported modes are:

- `none`: remove client authorization before forwarding and inject no credential.
- `passthrough_bearer`: retain the client's Bearer credential for a legacy HTTP target. This is allowed only with client-key gateway authentication and is not MCP OAuth compliance.
- `static_bearer`: read a target token from an owner-only secret file and inject `Authorization: Bearer ...`.
- `static_api_key`: read a target key from an owner-only secret file and inject it into an explicitly configured non-reserved header with an optional prefix.

The legacy 0.36 `destination_auth` and `bearer_file` fields remain accepted and are normalized into the new target model. New documentation uses `target_auth`.

## Request data flow

1. The gateway parses headers and rejects duplicates before reading the body.
2. Public OAuth resource metadata is served locally and never forwarded.
3. The configured gateway authenticator validates the client-key or JWT.
4. Exact method/path route admission and session/upgrade/content constraints are enforced.
5. Gateway credentials and reserved forwarding headers are removed.
6. The target credential provider injects the configured target credential.
7. The final serialized request is signed with the trusted-hop attestation and sent only to Envoy.
8. Envoy and the inspector enforce action, PII, secret, source, replay, and response policy before the fixed destination is reached.

No token values, key values, JWT claims, or target credential values are written to audit evidence.

## MCP and HTTP compatibility

0.37 will verify three client paths:

- The pinned official Python MCP SDK performs `initialize`, `notifications/initialized`, and `tools/list` over Streamable HTTP through the gateway.
- A generic HTTP client exercises client-key and JWT modes.
- A documented VS Code remote MCP configuration uses the supported `url`, `type`, and `headers` fields. This is configuration compatibility evidence, not automated execution of the VS Code product.

The compatibility document records whether each path was source-reviewed, synthetically integrated, or manually verified. It must not describe a documented configuration example as a live client test.

## OAuth, session, and SSE boundary

Community 0.37 will not implement an authorization endpoint, token endpoint, Dynamic Client Registration, browser callback, refresh-token store, on-behalf-of exchange, or third-party OAuth credential manager. Deployments use an existing authorization server.

The self-hosted gateway remains stateless for MCP. It rejects `Mcp-Session-Id`, `Set-Cookie`, long-lived SSE, WebSocket, and upgrade traffic. The inspection engine's bounded SSE support remains a separate capability and does not make this Docker gateway a streaming transport proxy.

Reuse decisions:

- Use PyJWT's `PyJWKClient` for cached JWKS retrieval and signature-key selection.
- Use the official MCP Python SDK for protocol compatibility testing.
- Evaluate a dedicated OAuth proxy or enterprise credential provider before adding authorization-code, DCR, OBO, or refresh-token behavior.
- Do not implement security-sensitive OAuth server behavior from scratch in Community.

## Failure behavior

- Missing or invalid gateway credentials: `401`, sanitized JSON, gateway-generated challenge in JWT mode.
- Valid JWT with insufficient scope: `403`, sanitized JSON and required-scope challenge.
- JWKS unavailable, malformed, or untrusted: fail closed with `401`; no target request.
- Conflicting target credential: `400`; no target request.
- Invalid configuration, insecure non-loopback metadata/JWKS URL, reserved API-key header, or JWT plus passthrough combination: startup validation failure.
- Target response authentication challenges remain suppressed because they describe the private target, not the public TrapDefense resource.
- Existing request-size, timeout, redirect, response-size, media-type, session, and inspection-path failures remain unchanged.

## Verification

Unit tests cover configuration normalization, HTTPS/loopback validation, JWT success and failure, scope handling, metadata and challenges, credential separation, and secret redaction boundaries.

Integration tests use an ephemeral RSA key and synthetic JWKS endpoint. They prove protocol behavior without claiming a real Entra tenant. The official MCP SDK test proves sessionless Streamable HTTP initialization and discovery through the actual FastAPI gateway and the mocked fixed Envoy hop.

The existing complete Python suite, console type/build checks, and opt-in Docker package test remain release gates. The Docker fixture verifies the new structured target credential configuration.

## Documentation and release

English remains canonical. The README and six self-hosting guides describe the two authentication boundaries, supported modes, compatibility matrix, and explicit limitations. Public version references and the self-hosted image tag move from 0.36 to 0.37.

No remote push, public release, landing-page deployment, real tenant change, or customer environment change is part of this implementation run.
