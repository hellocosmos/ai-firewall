# Alcance de seguridad y notificación

[English](../en/security.md) · [한국어](../ko/security.md) · [简体中文](../zh-CN/security.md) · [日本語](../ja/security.md) · [Español](../es/security.md) · [Français](../fr/security.md)

Community incluye SSO de consola Microsoft Entra ID de un solo tenant, con roles Administrador y Lector. La autenticación de consola no autoriza acciones de agentes; delegación y aprobación siguen en Enterprise. [Entra SSO](identity.md).

Notifique vulnerabilidades en privado a **hellocosmos@gmail.com** , indicando revisión, reproducción sintética e impacto. No incluya datos de clientes, tokens ni credenciales reales en incidencias públicas. No se promete un SLA de respuesta fijo.

## Cobertura PII

La inspección sin conexión evalúa los seis perfiles de idioma para cada carga compatible:

- Inglés: correo electrónico, teléfono, tarjeta de crédito, IBAN y SSN estadounidense.
- Coreano: registros de residente y extranjero, permiso de conducir, pasaporte y registro empresarial.
- Chino simplificado: teléfono y número de identidad de residente GB 11643.
- Japonés: teléfono y número individual de 12 dígitos (My Number).
- Español: teléfono, NIF, NIE y pasaporte.
- Francés: teléfono y número de seguridad social NIR, incluidos códigos de Córcega.

Los identificadores nacionales validan formato y suma de comprobación cuando la norma la define. Es inspección determinista de patrones, no NER general: nombres, ubicaciones, direcciones postales, imágenes, OCR y archivos arbitrarios quedan fuera de esta versión.

El perímetro cubre tráfico HTTP/MCP compatible, enrutado explícitamente desde un salto firmado de confianza. Los ejemplos locales son demostraciones sintéticas, no equipos de producción endurecidos.

- Limite los listeners de texto claro, ExtProc y mirror a redes y remitentes de confianza.
- Proteja y rote las claves de firma; nunca las entregue a agentes. Imponga rutas al destino para evitar desvíos.
- Los fallos inline del inspector o de autorización deben bloquear. El colector mirror separado no bloquea originales; Mirror de la consola usa una ruta síncrona y bloquea si falla la comunicación con el inspector.
- Configure límites de cuerpo/tiempo, mapeos y ocultación por campo. SSE con búfer tiene límites, no es streaming ilimitado.
- La protección de repetición y auditoría SQLite local no garantiza HA distribuida ni retención inmutable.
- La detección de patrones y PII tiene falsos positivos y negativos.
- Un origen firmado no acredita la identidad humana o del agente. Enterprise exige una cadena de identidad de confianza independiente.

La cuenta inicial es `admin` con contraseña `1234`; cámbiela en Configuración. La gestión escucha en loopback. La configuración de red administra el contenedor Envoy propio de la demo, no direcciones de interfaces del SO, rutas físicas ni reglas de firewall. Autenticación, controles CSRF y hashes no convierten esta demo sintética en IAM de producción. MIT cubre Community; se excluyen implementación privada y activos de clientes.
