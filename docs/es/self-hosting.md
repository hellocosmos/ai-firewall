# Autoalojamiento con Docker — 0.37 Community Preview

[English](../en/self-hosting.md) · [한국어](../ko/self-hosting.md) · [简体中文](../zh-CN/self-hosting.md) · [日本語](../ja/self-hosting.md) · [Español](../es/self-hosting.md) · [Français](../fr/self-hosting.md)

0.37 ofrece adaptador, Envoy, inspector, consola y autenticación separada para gateway y destino. La imagen se compila localmente desde el código fuente. TrapDefense Cloud sigue previsto.

El cliente debe poder cambiar la URL MCP/API y usar `X-TD-Client-Key` o un JWT Bearer OAuth. Cada despliegue tiene un destino fijo y rutas/herramientas explícitas. Consulte la [matriz de compatibilidad](gateway-compatibility.md).

| Tipo | Contrato |
|---|---|
| HTTP API | JSON, method/path exactos, máximo 1 MiB, respuesta acotada |
| MCP | POST JSON sin estado, métodos de control y herramientas explícitos |
| Autenticación del gateway | Clave o JWT RS256 de IdP externo con issuer/audience/scope y metadatos RFC 9728 |
| Autenticación del destino | none, paso Bearer heredado, Bearer/API Key fijo desde archivo |
| No compatible | Emisión OAuth, login intermediado, DCR, OBO, cookies/sesiones, SSE prolongado, WebSocket, stdio, SaaS interno cerrado |

La contraseña administra la consola. La clave o JWT autentica el acceso a TrapDefense. El JWT se valida para el audience del gateway y no se reenvía al destino, que usa una credencial separada. Esto no registra Agent IAM ni implementa un OAuth Authorization Server.

## Docker

Requiere Git y Docker Compose v2. init solicita una contraseña de administrador de al menos 12 caracteres, sin valor predeterminado. El ejemplo apunta a un destino sintético, no a un servicio real.

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall/deploy/selfhost
docker compose build app
docker compose run --rm app init
docker compose --profile smoke up -d
docker compose run --rm app client-key
```

Inicie sesión como admin en http://localhost:18080. Lea la clave con client-key y guárdela en los encabezados secretos del cliente. El gateway está en http://localhost:18084; el token del destino sintético es Bearer synthetic-target-token.

Para su servicio, cambie upstream, authority, rutas, herramientas y resource. `gateway_auth` admite `client_key` o `jwt`; `target_auth` admite `none`, `passthrough_bearer`, `static_bearer` y `static_api_key`. JWT y passthrough no se combinan. Las credenciales fijas usan un archivo 0600 legible por UID 10001 y rechazan entradas en conflicto.

La UI gestiona políticas y contraseñas. Para cambiar mapeos: haga copia, ejecute policy-reset, render y recree el despliegue. Solo se reinician las políticas guardadas; cuentas, claves y eventos se conservan. Las nuevas solicitudes usan la política actualizada.

Los puertos se enlazan a loopback. El uso remoto necesita proxy TLS y console_origin exacto. Inspector y Envoy no publican puertos del host. Evite rutas de evasión con controles de red.

El estado persiste en volúmenes. Detenga y respalde ambos volúmenes y la configuración. down -v destruye datos. Para revertir, restaure la imagen anterior y su copia correspondiente. Un listener sano no prueba autenticación: verifique solicitudes permitidas/bloqueadas y efectos en el destino. Streaming prolongado, HA e IAM real requieren validación adicional.

[Compatibilidad y VS Code](gateway-compatibility.md) · [Detailed examples, backup and migration (English)](../en/self-hosting.md)
