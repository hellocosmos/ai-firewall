# TrapDefense Community 0.38 Compatibility Lab Design

## Goal

Create reproducible evidence that the Community gateway interoperates with standards-shaped OAuth providers and current MCP clients without claiming untested vendor or production behavior.

## Evidence levels

1. **Source contract**: configuration and protocol behavior are checked directly in source and tests.
2. **Synthetic protocol integration**: an in-process authorization server implements discovery, dynamic registration, authorization code with PKCE, resource indicators, token issuance and JWKS.
3. **Real local integration**: an unmodified official Keycloak container issues a token that the gateway validates.
4. **Real client integration**: an installed VS Code client connects to a local synthetic gateway and completes MCP initialization and tool discovery.
5. **Production validation**: real tenant policy, public TLS, Conditional Access, revocation, customer routing and multi-node operations. This level remains outside 0.38.

## Scope

### Provider-shaped OAuth profiles

The synthetic authorization server emits standards-valid RS256 access tokens with representative claim dialects:

- Microsoft Entra ID v2: `scp`, `tid`, `oid`, `azp`
- Okta custom authorization server: `scp`, `cid`
- Keycloak: `scope`, `azp`, `realm_access`

Every profile must complete the same external flow through the official MCP Python SDK:

1. Request the MCP endpoint without a token.
2. Receive a gateway-owned `WWW-Authenticate` challenge.
3. Discover RFC 9728 Protected Resource Metadata.
4. Discover authorization-server metadata.
5. Register a synthetic public client.
6. Complete authorization code with PKCE and RFC 8707 `resource` binding.
7. Exchange the code for an RS256 access token.
8. Validate issuer, audience, time, subject and scope at TrapDefense.
9. Complete MCP `initialize`, `notifications/initialized` and `tools/list` using protocol version `2025-11-25`.

The harness must also prove that a token from one provider profile is rejected by a gateway configured for another issuer.

### Real Keycloak

Use the official pinned Keycloak container in development mode with an imported synthetic realm. The test obtains a client-credentials token from Keycloak's real token endpoint, reads its real discovery/JWKS documents and sends the token through the gateway. The realm contains only synthetic credentials and is deleted with the container.

This proves local Keycloak interoperability. It does not prove production TLS, external database, cluster cache, user login, DCR policy or customer realm configuration.

### VS Code

Run the installed VS Code in an isolated temporary user-data directory and workspace. The generated workspace configuration points only to a loopback synthetic gateway. Validation requires visible MCP connection evidence from VS Code plus a matching server-side initialize/discovery receipt.

If the installed build or account state prevents unattended activation, record the exact boundary and keep the generated fixture for a later interactive run. Configuration-file creation alone is not a passing result.

### Stateful MCP, SSE and HA

0.38 records executable negative boundaries for the current profile:

- inbound `MCP-Session-Id` is rejected;
- upstream `MCP-Session-Id` is rejected;
- upstream `text/event-stream` is rejected;
- the package remains a single gateway instance with local state.

These checks prevent accidental claims of support. Stateful MCP/SSE require streaming inspection, session lifecycle, cancellation and replay design. HA requires replica-safe policy, keys, replay state, audit and session routing. They are separate implementation releases.

## Security constraints

- Synthetic tokens and credentials use reserved test values only.
- Raw tokens, codes and secrets never enter audit evidence or committed output.
- Authorization-server and JWKS URLs remain HTTPS except explicit loopback test mode.
- Gateway access tokens are consumed at the gateway and never forwarded to the target.
- Provider-shaped claims are compatibility inputs, not Agent IAM identities.
- Tests fail closed for wrong issuer, audience, signature, scope, state, PKCE or resource.

## Release result

0.38 may claim standards-shaped Entra/Okta/Keycloak OAuth compatibility, real local Keycloak token validation, and current official MCP SDK interoperability only when those tests pass. VS Code receives its own evidence label. Stateful MCP, SSE and multi-node HA remain unsupported until implemented.
