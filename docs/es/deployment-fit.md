# Compatibilidad y disponibilidad

> **AISG:** [Conectar, identificar, controlar, verificar](aisg.md). El gateway autentica con una clave de despliegue o JWT verificado. agent_key identifica agentes registrados sin IAM externo. JWT identity_mode: agent usa los atributos verificados de tenant y agente; delegated también exige usuario, tarea y delegación. Los agentes existentes requieren delegación por defecto.

[English](../en/deployment-fit.md) · [한국어](../ko/deployment-fit.md) · [简体中文](../zh-CN/deployment-fit.md) · [日本語](../ja/deployment-fit.md) · [Español](../es/deployment-fit.md) · [Français](../fr/deployment-fit.md)

Proteja llamadas HTTP API y MCP remoto que pueda dirigir por una ruta de inspección compatible. Mantenga la autenticación existente en servidores MCP y conectores; no sustituya su IAM.

0.42 ofrece un paquete Docker Compose con clave o JWT externo para el gateway y credenciales independientes para el destino. La imagen se compila desde fuentes; TrapDefense Cloud sigue previsto.

Debe controlar el endpoint del cliente, la entrada del servidor o una ruta de inspección de red compatible. Se requiere conectividad al destino y evitar rutas alternativas. Las llamadas internas de SaaS, stdio local, shell, archivos y acceso directo a bases de datos quedan fuera del proxy HTTP.

La evidencia actual incluye OpenAI real con MCP sintético, fixtures de SDK oficiales, MCP/Keycloak locales reales e inicialización/descubrimiento de VS Code. El SSE de modelos se almacena completo; MCP con estado, IAM de clientes, HA entre hosts y capacidad productiva no están certificados. Consulte [validación y límites de 0.42](agent-workflow.md).

[Architecture](architecture.md) · [Delivery status](editions.md) · [MCP pilot](mcp-pilot.md)

[Autoalojamiento con Docker](self-hosting.md) · [Compatibilidad del gateway](gateway-compatibility.md)
