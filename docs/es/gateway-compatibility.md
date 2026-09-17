# Compatibilidad de clientes del gateway — 0.38

[English](../en/gateway-compatibility.md) · [한국어](../ko/gateway-compatibility.md) · [简体中文](../zh-CN/gateway-compatibility.md) · [日本語](../ja/gateway-compatibility.md) · [Español](../es/gateway-compatibility.md) · [Français](../fr/gateway-compatibility.md)

El cliente debe poder cambiar la URL HTTP/MCP remota a TrapDefense y enviar una clave de conexión o un JWT Bearer OAuth. La autenticación cliente→TrapDefense se mantiene separada de TrapDefense→destino.

| Ruta | Evidencia de 0.38 |
|---|---|
| JSON HTTP genérico | Integración sintética verificada con HTTPX |
| SDK oficial de Python MCP 1.30.0 | Inicialización, notificación y lista de herramientas MCP `2025-11-25` verificadas en integración sintética |
| OAuth con forma de Entra | `scp`, `tid`, `oid`, `azp`, discovery, DCR, PKCE y resource binding verificados sintéticamente; no es un tenant Entra real |
| OAuth con forma de Okta | `scp` como array y `cid` verificados en el flujo sintético completo; no es un servidor Okta real |
| Keycloak sintético / local real | Además del flujo sintético, un Keycloak 26.7.3 oficial fijado por digest emitió un token local real validado con su discovery y JWKS |
| MCP remoto de VS Code 1.135 | Se confirmó que reconoce la configuración del workspace; esta ejecución no capturó el inicio ni los receipts, por lo que la conexión real sigue sin verificarse |
| MCP con estado, SSE prolongado, WebSocket, stdio | No admitidos; session headers y upstream SSE fallan de forma cerrada |
| HA multinodo | No admitida; una instancia con SQLite, replay y audit state locales |

`gateway_auth` usa `client_key` o `jwt`. En modo JWT, TrapDefense es un OAuth Resource Server con metadata RFC 9728 y `WWW-Authenticate`. `scope`/`scp` puede ser una cadena separada por espacios o un array; `authorized_parties` opcional limita `azp`, `appid` o `cid`. En 0.38, los app roles de Entra en `roles` no se interpretan como scopes.

`target_auth` admite `none`, `passthrough_bearer`, `static_bearer` y `static_api_key`. El JWT del gateway no llega al destino. El IdP externo o un credential provider separado gestiona login, emisión, refresh y OBO.

Antes de aprobar una integración, verifique URL, ambas autenticaciones, inicialización/descubrimiento MCP, acciones permitidas y denegadas, efectos en destino, PII/secret, 401 del destino, fallo de inspección y ausencia de fallback directo. Consulte comandos, configuración y fuentes en la [guía inglesa](../en/gateway-compatibility.md).
