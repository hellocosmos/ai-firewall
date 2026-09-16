# Alcance de seguridad y notificación

[English](../en/security.md) · [한국어](../ko/security.md) · [简体中文](../zh-CN/security.md) · [日本語](../ja/security.md) · [Español](../es/security.md) · [Français](../fr/security.md)

Notifique vulnerabilidades en privado a **hellocosmos@gmail.com** , indicando revisión, reproducción sintética e impacto. No incluya datos de clientes, tokens ni credenciales reales en incidencias públicas. No se promete un SLA de respuesta fijo.

El perímetro cubre tráfico HTTP/MCP compatible, enrutado explícitamente desde un salto firmado de confianza. Los ejemplos locales son demostraciones sintéticas, no equipos de producción endurecidos.

- Limite los listeners de texto claro, ExtProc y mirror a redes y remitentes de confianza.
- Proteja y rote las claves de firma; nunca las entregue a agentes. Imponga rutas al destino para evitar desvíos.
- Los fallos inline del inspector o de autorización deben bloquear. El colector mirror separado no bloquea originales; Mirror de la consola usa una ruta síncrona y bloquea si falla la comunicación con el inspector.
- Configure límites de cuerpo/tiempo, mapeos y ocultación por campo. SSE con búfer tiene límites, no es streaming ilimitado.
- La protección de repetición y auditoría SQLite local no garantiza HA distribuida ni retención inmutable.
- La detección de patrones y PII tiene falsos positivos y negativos.
- Un origen firmado no acredita la identidad humana o del agente. Enterprise exige una cadena de identidad de confianza independiente.

La cuenta inicial es `admin` con contraseña `1234`; cámbiela en Configuración. La gestión escucha en loopback. La configuración de red administra el contenedor Envoy propio de la demo, no direcciones de interfaces del SO, rutas físicas ni reglas de firewall. Autenticación, controles CSRF y hashes no convierten esta demo sintética en IAM de producción. MIT cubre Community; se excluyen implementación privada y activos de clientes.
