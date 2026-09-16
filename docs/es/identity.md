# Microsoft Entra ID — Community console SSO

[English](../en/identity.md) · [한국어](../ko/identity.md) · [简体中文](../zh-CN/identity.md) · [日本語](../ja/identity.md) · [Español](../es/identity.md) · [Français](../fr/identity.md)

Community incluye SSO de consola Microsoft Entra ID de un solo tenant, con roles Administrador y Lector. La autenticación de consola no autoriza acciones de agentes; delegación y aprobación siguen en Enterprise.

## Configuration

Registre una aplicación Web de un solo tenant con la URL de retorno exacta indicada abajo. Cree roles de usuario `TrapDefense.Admin` y `TrapDefense.Viewer`, exija asignación en Aplicaciones empresariales y asigne usuarios de prueba. Guarde la configuración fuera del repositorio con permisos 0600. El secreto permanece en el servidor; no requiere permisos de Graph.

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

El Lector consulta panel, eventos, política, red y auditoría; el servidor rechaza escrituras salvo cerrar sesión. Las contraseñas Entra se gestionan allí. Sesiones de máximo una hora, limitadas por el ID token. Los cambios de rol se aplican al siguiente acceso; no hay revalidación continua. Cerrar sesión termina solo la sesión local. Entra real desactiva el acceso local por defecto; cambie la contraseña inicial antes de activar recuperación con `TD_CONSOLE_LOCAL_LOGIN=1`. Consola solo loopback. La prueba sintética no valida tenant real, consentimiento, MFA ni acceso condicional.

## Protocol

Authorization code + PKCE S256, browser-bound one-time state, nonce, RS256 signature, issuer, audience, tenant and app-role validation. Tokens and client secrets are never sent to browser storage or audit logs. Synthetic mode uses an ephemeral RSA issuer with local code redemption; no Microsoft token endpoint is called. Real mode uses Microsoft authorization/token/JWKS endpoints and does not register synthetic routes.

[Microsoft authorization code flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow)
