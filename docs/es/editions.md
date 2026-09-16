# Community y Enterprise

[English](../en/editions.md) · [한국어](../ko/editions.md) · [简体中文](../zh-CN/editions.md) · [日本語](../ja/editions.md) · [Español](../es/editions.md) · [Français](../fr/editions.md)

Community es el runtime de proxy y la consola local con licencia MIT de este repositorio. Incluye verificación de salto firmado, mapeos HTTP/MCP explícitos, política local, detección por patrones, ocultación de PII, inspección limitada de respuestas/SSE, auditoría depurada, inicio de sesión local, cambio de contraseña y configuración del proxy. No requiere paquetes privados ni API de modelos externos.

Enterprise añade Access Broker, distribuido por separado: delegación de usuario/agente/tarea, decisiones de acceso y aprobación humana de un solo uso, con caducidad y vinculada a la solicitud. El contexto IAM debe llegar mediante una integración de confianza; sigue siendo necesaria la validación con el IdP real del cliente. La UI Community señala las funciones no incluidas.

El proveedor privado usa el punto de entrada Python `trapdefense.authorizers` / `enterprise`. `authorize(request)` aplica las decisiones; `evaluate(request)` evalúa mirror sin modificar estado. Elegir Enterprise sin proveedor impide iniciar. Los registros de tokens del Broker son pruebas de decisiones acotadas, no tokens OAuth de uso general.

La gestión centralizada, HA distribuida, facturación alojada y almacenamiento de auditoría inmutable no se ofrecen. El alcance comercial puede incluir proveedor privado, despliegue, integración de políticas y soporte; precios y condiciones se acuerdan aparte. SQLite y JSONL locales siguen siendo modificables.
