# Arquitectura y límite de confianza

[English](../en/architecture.md) · [한국어](../ko/architecture.md) · [简体中文](../zh-CN/architecture.md) · [日本語](../ja/architecture.md) · [Español](../es/architecture.md) · [Français](../fr/architecture.md)

## Plano de datos y de control

La API autentica al operador local, guarda políticas y sirve la UI. Envoy reenvía HTTP/MCP admitido y llama al inspector mediante gRPC ExtProc para solicitudes y respuestas. Cada flujo conserva una instantánea de política. Un destino HTTP sintético sin acciones empresariales aporta recibos. Consulte la [instalación](console.md).

## Contrato de confianza

1. Fuerce las rutas fuera de TrapDefense para impedir el bypass del proxy.
2. Use un descifrador TLS existente y autorizado. La demo no descifra TLS de producción.
3. El adaptador de confianza elimina `x-td-*` y `x-asr-*` del cliente y firma lo que observó. Preserve método, autoridad, ruta/consulta, cabeceras de aplicación y cuerpo completo. `inspection/identity.py` define la vinculación y exclusiones.
4. Guarde la clave HMAC solo en el salto de confianza y el inspector, nunca en agentes. Permita explícitamente `source_id` en Community. Aísle texto claro y ExtProc: los ejemplos no autentican una escucha gRPC pública.
5. Envoy usa búfer completo, límites de tamaño/tiempo y `failure_mode_allow: false`. Elimina la atestación antes de reenviar. La firma vincula el original; una aprobación persistente, si existe, vincula el resumen de la acción después de ocultar datos.
6. Community aplica reglas locales explícitas de ruta/herramienta/recurso/acción y verifica el origen. No establece identidad de usuario ni autoridad delegada del agente.
7. Enterprise valida identidad/delegación con un proveedor privado independiente. Las configuraciones anteriores mantienen Enterprise por defecto; la falta del proveedor impide iniciar, sin degradación silenciosa.

No existe adaptador universal para cualquier equipo TLS. La integración debe evitar suplantación de metadatos y restringir el acceso directo al destino.

## Cobertura y límites

Las rutas exigen coincidencia exacta de autoridad, método, ruta y cabeceras. MCP cubre llamadas JSON-RPC asignadas y versiones configuradas, no certifica todas sus funciones. Transportes arbitrarios, túneles WebSocket, cuerpos cifrados opacos, CONNECT sin restricciones y descubrimiento automático quedan fuera. Solo se modifican campos/formatos permitidos; transformaciones inseguras se bloquean. Las firmas detectan patrones conocidos acotados, sin garantía frente a toda inyección. SSE almacena un flujo completo y limitado, no streaming ilimitado token a token.

El colector mirror independiente recibe copias y no afecta al original; con solo cabeceras la cobertura es incompleta. Mirror de la consola observa su ruta síncrona sin modificar cuerpo, pero el fallo de comunicación del inspector bloquea. Distinga ambos en despliegues e informes. JSONL y auditoría SQLite omiten contenido original y claves; son almacenamiento local modificable, no retención inmutable.

## Perfil de red

La consola usa loopback y una imagen Envoy amd64/arm64 fijada por digest. macOS usa Docker Desktop hacia el host; Linux, host networking. El inventario enumera interfaces del SO, no puertos físicos. Enrutamiento de dos NIC, puente transparente, salida física fijada, IdP/TLS reales, HA y rendimiento requieren trabajo separado. Las pruebas opcionales agentgateway son compatibilidad, no un servicio gestionado.
