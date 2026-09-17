# Community y Enterprise

[English](../en/editions.md) · [한국어](../ko/editions.md) · [简体中文](../zh-CN/editions.md) · [日本語](../ja/editions.md) · [Español](../es/editions.md) · [Français](../fr/editions.md)

## Compatibilidad y disponibilidad

0.38 ofrece un paquete Docker Compose con clave o JWT externo para el gateway y credenciales independientes para el destino. La imagen se compila desde fuentes; TrapDefense Cloud sigue previsto.

[Entrega y compatibilidad](deployment-fit.md)

Community incluye SSO de consola Microsoft Entra ID de un solo tenant, con roles Administrador y Lector. La autenticación de consola no autoriza acciones de agentes; delegación y aprobación siguen en Enterprise. [Entra SSO](identity.md).

## Estado actual de entrega

| Límite | Estado | Evidencia y límite |
|---|---|---|
| Runtime y consola Community | **Community Preview público** | Publicado en este repositorio MIT; CI y la verificación sintética de la ruta Envoy pasan. El tráfico y la capacidad de producción requieren validación del cliente. |
| Enterprise Access Broker | **Implementación piloto privada** | Existen el proveedor y el flujo de aprobación distribuidos aparte; no están en este repositorio ni se presentan como disponibilidad general. Requieren IAM real, política del cliente y validación de fallos. |
| Fleet central, HA distribuida, auditoría inmutable y servicio alojado | **Hoja de ruta** | No entregados ni representados como funciones por las pantallas Community. |

Los nombres de edición definen límites de producto y licencia; no afirman disponibilidad general de toda la hoja de ruta Enterprise.

Community es el runtime de proxy y la consola local con licencia MIT de este repositorio. Incluye verificación de salto firmado, mapeos HTTP/MCP explícitos, política local, detección por patrones, ocultación de PII, inspección limitada de respuestas/SSE, auditoría depurada, inicio de sesión local, cambio de contraseña y configuración del proxy. No requiere paquetes privados ni API de modelos externos.

La implementación piloto Enterprise distribuida por separado añade Access Broker: delegación de usuario/agente/tarea, decisiones de acceso y aprobación humana de un solo uso, con caducidad y vinculada a la solicitud. El contexto IAM debe llegar mediante una integración de confianza; sigue siendo necesaria la validación con el IdP real del cliente. La UI Community señala las funciones no incluidas.

El proveedor privado usa el punto de entrada Python `trapdefense.authorizers` / `enterprise`. `authorize(request)` aplica las decisiones; `evaluate(request)` evalúa mirror sin modificar estado. Elegir Enterprise sin proveedor impide iniciar. Los registros de tokens del Broker son pruebas de decisiones acotadas, no tokens OAuth de uso general.

La gestión centralizada, HA distribuida, facturación alojada y almacenamiento de auditoría inmutable no se ofrecen. El alcance comercial puede incluir proveedor privado, despliegue, integración de políticas y soporte; precios y condiciones se acuerdan aparte. SQLite y JSONL locales siguen siendo modificables.

[Docker 0.38](self-hosting.md) · [Compatibilidad del gateway](gateway-compatibility.md)
