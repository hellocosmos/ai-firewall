# Microsoft Entra ID — Community console SSO

[English](../en/identity.md) · [한국어](../ko/identity.md) · [简体中文](../zh-CN/identity.md) · [日本語](../ja/identity.md) · [Español](../es/identity.md) · [Français](../fr/identity.md)

Community includes single-tenant Microsoft Entra ID console SSO with Administrator and Viewer roles. Console authentication does not authorize agent actions; delegation and approval remain Enterprise features.

## Configuration

Create a single-tenant Web app registration. Register the exact callback below. Define user app roles `TrapDefense.Admin` and `TrapDefense.Viewer`, enable assignment requirements in Enterprise applications, and assign test users. Store the configuration outside the repository with mode 0600. The secret stays on the server; no Graph permission is required.

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

## Synthetic demo

```bash
TD_SYNTHETIC_ENTRA=1 ./scripts/run-console.sh
```

`http://127.0.0.1:5176` → **Sign in with Synthetic Entra** → **Admin / Viewer**.

Viewer can read dashboard, events, policy, network and audit; all writes except logout are denied server-side. Entra users manage passwords in Entra. Sessions last at most one hour and never beyond ID-token expiry. Role changes take effect at next sign-in; existing sessions are not continuously revalidated. Logout ends the local session, not the Microsoft session. Real Entra defaults to local login disabled; `TD_CONSOLE_LOCAL_LOGIN=1` explicitly enables the local recovery account. Change its default password before enabling it. The console remains loopback-only. Synthetic success is not real tenant, consent, MFA or Conditional Access evidence.

## Protocol

Authorization code + PKCE S256, browser-bound one-time state, nonce, RS256 signature, issuer, audience, tenant and app-role validation. Tokens and client secrets are never sent to browser storage or audit logs. Synthetic mode uses an ephemeral RSA issuer with local code redemption; no Microsoft token endpoint is called. Real mode uses Microsoft authorization/token/JWKS endpoints and does not register synthetic routes.

[Microsoft authorization code flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow)
