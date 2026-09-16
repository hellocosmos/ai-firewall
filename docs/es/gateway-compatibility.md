# Compatibilidad de clientes del gateway — 0.37

[English](../en/gateway-compatibility.md) · [한국어](../ko/gateway-compatibility.md) · [简体中文](../zh-CN/gateway-compatibility.md) · [日本語](../ja/gateway-compatibility.md) · [Español](../es/gateway-compatibility.md) · [Français](../fr/gateway-compatibility.md)

El cliente debe poder cambiar la URL HTTP/MCP remota a TrapDefense y usar una cabecera con clave de conexión o un JWT Bearer de OAuth. La autenticación cliente→TrapDefense está separada de la autenticación TrapDefense→destino.

| Ruta | Evidencia de 0.37 |
|---|---|
| JSON HTTP genérico | Integración sintética verificada con HTTPX |
| SDK oficial de Python MCP 1.30.0 | El SDK real completó inicialización, notificación y lista de herramientas por Streamable HTTP contra un destino sintético |
| MCP remoto de VS Code | Configuración compatible con `url`, `headers` y OAuth oficiales; ejecución dentro de VS Code aún no verificada |
| Metadatos OAuth y JWT RS256 | Obtención HTTP real de JWKS y validación sintética de issuer/audience/time/subject/scope |
| Entra/Okta/Keycloak real | Requiere validar tenant, TLS, Conditional Access y revocación |
| MCP con estado, SSE prolongado, WebSocket, stdio | No admitido en este perfil |

`gateway_auth` usa `client_key` o `jwt`. En modo JWT, TrapDefense actúa como OAuth Resource Server y publica metadatos RFC 9728 y el reto `WWW-Authenticate`. El IdP externo o un proveedor de credenciales separado gestiona inicio de sesión, emisión, DCR, renovación y OBO.

`target_auth` admite `none`, `passthrough_bearer`, `static_bearer` y `static_api_key`. El JWT del gateway no se reenvía al destino. `passthrough_bearer` sirve solo para incorporar HTTP heredado con client-key y no implica conformidad con OAuth MCP.

Antes de aprobar una integración, verifique URL, ambas autenticaciones, inicialización/descubrimiento MCP, acciones permitidas y denegadas, efectos en destino, PII/secret, 401 del destino, fallo de inspección y ausencia de fallback directo. Consulte configuración y ejemplo de VS Code en la [guía inglesa](../en/gateway-compatibility.md).
