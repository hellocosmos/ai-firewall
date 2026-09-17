# Identity boundaries: console operators and agents

[English](../en/identity.md) · [한국어](../ko/identity.md) · [简体中文](../zh-CN/identity.md) · [日本語](../ja/identity.md) · [Español](../es/identity.md) · [Français](../fr/identity.md)

TrapDefense has two separate identity paths:

1. **Console operator identity** controls who can view or change policy, agents, delegations, and approvals. The console supports local administration and single-tenant Microsoft Entra ID SSO with Administrator and Viewer roles.
2. **Agent request identity** controls whether a routed action may execute. A self-hosted gateway verifies an external JWT and maps an explicit allowlist of claims into the built-in Access Broker.

An operator login never becomes an agent identity. A trusted-hop signature proves adapter/request binding, not a user or agent.

## Console Entra configuration

Create a single-tenant Web app registration and register the exact callback. Define user app roles `TrapDefense.Admin` and `TrapDefense.Viewer`, require assignment in the Entra Enterprise application, and assign test users. Keep the server-side configuration outside the repository with mode 0600. No Microsoft Graph permission is required.

```json
{
  "tenant_id": "YOUR-TENANT-UUID",
  "client_id": "YOUR-APPLICATION-UUID",
  "client_secret": "YOUR-SERVER-SIDE-SECRET",
  "redirect_uri": "http://localhost:5176/demo-api/auth/callback"
}
```

```bash
chmod 600 /absolute/path/entra.json
TD_ENTRA_CONFIG=/absolute/path/entra.json ./scripts/run-console.sh
```

Viewer access is read-only server-side. Entra users manage passwords in Entra. Sessions never outlive the validated ID-token expiry. Synthetic Entra uses an ephemeral local issuer and is not evidence of real consent, MFA, Conditional Access, Microsoft signing keys, or role propagation.

## Agent JWT claim mapping

The Docker gateway accepts RS256 tokens for the configured issuer, audience, resource, scopes, and optional authorized party. When `access_broker.enabled` is true, `gateway_auth.identity_claims` is mandatory. Required mapped values are tenant, user, agent, delegation, and task. Optional values are agent instance and approval ID.

Only mapped values enter the trusted attestation. Arbitrary JWT claims and the gateway token itself are not copied into inspection evidence or forwarded to the target. The configured broker tenant must match the mapped tenant. Missing, empty, oversized, or non-string identity claims fail closed.

The external IdP may be Entra, Okta, Keycloak, or another compatible issuer. TrapDefense does not prescribe how that issuer creates agent/delegation claims; the customer must bind them to a trustworthy workload and lifecycle. Target-service credentials and permissions remain independent.

[Self-hosting configuration](self-hosting.md) · [Security](security.md) · [Synthetic compatibility evidence](gateway-compatibility.md)
