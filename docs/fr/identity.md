# Microsoft Entra ID — Community console SSO

[English](../en/identity.md) · [한국어](../ko/identity.md) · [简体中文](../zh-CN/identity.md) · [日本語](../ja/identity.md) · [Español](../es/identity.md) · [Français](../fr/identity.md)

Community inclut le SSO de console Microsoft Entra ID à locataire unique, avec les rôles Administrateur et Lecteur. L’authentification de console n’autorise pas les actions des agents ; délégation et approbation restent dans Enterprise.

## Configuration

Enregistrez une application Web à locataire unique avec l’URL de retour exacte ci-dessous. Créez les rôles utilisateur `TrapDefense.Admin` et `TrapDefense.Viewer`, exigez une affectation dans Applications d’entreprise et affectez les utilisateurs de test. Conservez la configuration hors du dépôt avec les permissions 0600. Le secret reste sur le serveur ; aucune permission Graph n’est nécessaire.

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

Le Lecteur consulte tableau de bord, événements, politique, réseau et audit ; le serveur refuse toute écriture sauf la déconnexion. Les mots de passe Entra se gèrent dans Entra. Sessions d’une heure maximum, bornées par l’expiration du jeton. Les changements de rôle prennent effet à la prochaine connexion, sans revalidation continue. La déconnexion termine uniquement la session locale. Entra réel désactive la connexion locale par défaut ; changez le mot de passe initial avant d’activer la récupération avec `TD_CONSOLE_LOCAL_LOGIN=1`. Console limitée au loopback. Le test synthétique ne valide ni locataire réel, consentement, MFA ni accès conditionnel.

## Protocol

Authorization code + PKCE S256, browser-bound one-time state, nonce, RS256 signature, issuer, audience, tenant and app-role validation. Tokens and client secrets are never sent to browser storage or audit logs. Synthetic mode uses an ephemeral RSA issuer with local code redemption; no Microsoft token endpoint is called. Real mode uses Microsoft authorization/token/JWKS endpoints and does not register synthetic routes.

[Microsoft authorization code flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow)
