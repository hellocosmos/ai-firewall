# TrapDefense Community 0.38 Compatibility Lab Implementation Plan

**Goal:** Produce reproducible provider, client and boundary evidence for the 0.38 gateway contract.

**Architecture:** Keep the production gateway provider-neutral. Put provider dialects and OAuth authorization-server behavior in test-only fixtures. Use the official MCP SDK for the full OAuth client flow and an unmodified official Keycloak container for real local IdP evidence.

**Tech stack:** Python 3.11+, FastAPI/ASGI, PyJWT, official MCP Python SDK 1.30.0, pytest, Docker, Keycloak 26.7.3, VS Code 1.135 or later.

---

## Task 1: Current MCP protocol compatibility

- Update the official SDK fixture to negotiate `2025-11-25`.
- Assert the client advertises the current protocol version.
- Retain generic JSON HTTP coverage.

## Task 2: Provider-shaped OAuth lab

- Build a test-only OAuth authorization server supporting metadata, JWKS, DCR, authorization code, PKCE and token exchange.
- Add Entra, Okta and Keycloak claim profiles.
- Drive the complete flow using `OAuthClientProvider` from the pinned official MCP SDK.
- Verify resource binding, discovery sequence, scope and token isolation.

## Task 3: Real Keycloak Docker integration

- Add a synthetic realm fixture with a service-account client, audience mapper and `mcp.invoke` client scope.
- Start the official pinned Keycloak image on loopback.
- Obtain a real access token and validate it through the gateway.
- Add an opt-in CI command and deterministic cleanup.

## Task 4: Real VS Code client attempt

- Add a loopback MCP fixture and generated workspace configuration.
- Launch the installed VS Code with isolated state.
- Verify client-visible connection and server-side MCP receipts.
- Record a concrete blocker if activation requires unavailable account or UI state.

## Task 5: Unsupported capability boundaries

- Add explicit regression tests for session headers and SSE rejection.
- Document why these are unsupported rather than presenting them as failed compatibility tests.
- Describe the implementation prerequisites for Stateful MCP/SSE and HA.

## Task 6: Release and documentation

- Bump package and console versions to 0.38.
- Update the English compatibility guide and concise localized summaries in all six languages.
- Update README and changelog claims to match actual evidence.
- Run focused tests, real Keycloak validation, the full Python suite, frontend checks/build and browser/UI review.
- Commit locally without pushing.
