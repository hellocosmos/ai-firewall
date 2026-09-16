# Compatibilidad y disponibilidad

[English](../en/deployment-fit.md) · [한국어](../ko/deployment-fit.md) · [简体中文](../zh-CN/deployment-fit.md) · [日本語](../ja/deployment-fit.md) · [Español](../es/deployment-fit.md) · [Français](../fr/deployment-fit.md)

Proteja llamadas HTTP API y MCP remoto que pueda dirigir por una ruta de inspección compatible. Mantenga la autenticación existente en servidores MCP y conectores; no sustituya su IAM.

0.37 ofrece un paquete Docker Compose con clave o JWT externo para el gateway y credenciales independientes para el destino. La imagen se compila desde fuentes; TrapDefense Cloud sigue previsto.

Debe controlar el endpoint del cliente, la entrada del servidor o una ruta de inspección de red compatible. Se requiere conectividad al destino y evitar rutas alternativas. Las llamadas internas de SaaS, stdio local, shell, archivos y acceso directo a bases de datos quedan fuera del proxy HTTP.

El piloto local 0.35 verifica Streamable HTTP sin estado con respuestas JSON. La inspección SSE limitada no certifica todos los servidores MCP con streaming. OAuth, sesiones con estado e identidad del cliente requieren validación. El SSO de consola Entra no es IAM de agentes ni autorización al destino.

[Architecture](architecture.md) · [Delivery status](editions.md) · [MCP pilot](mcp-pilot.md)

[Autoalojamiento con Docker](self-hosting.md) · [Compatibilidad del gateway](gateway-compatibility.md)
