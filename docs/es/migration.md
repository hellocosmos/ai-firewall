# Migración desde el SDK anterior

[English](../en/migration.md) · [한국어](../ko/migration.md) · [简体中文](../zh-CN/migration.md) · [日本語](../ja/migration.md) · [Español](../es/migration.md) · [Français](../fr/migration.md)

El SDK Python embebido anterior y su historial permanecen en [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security). Este repositorio es el nuevo producto proxy Community. No implica compatibilidad SDK ni migración automática de paquetes.

1. Inventaríe las llamadas HTTP/MCP y destinos que debe proteger.
2. Sitúe un adaptador de firma de confianza después del descifrado TLS y fuerce el paso por el proxy.
3. Configure mapeos explícitos de herramientas/acciones, límites y campos de ocultación.
4. Observe datos sintéticos y luego valide permiso, ocultación, bloqueo y fallos inline.
5. Añada el proveedor privado Enterprise cuando necesite acceso delegado y aprobación vinculada a la solicitud.

Los usuarios del SDK pueden mantener versiones fijadas mientras evalúan un piloto con ruta separada. Consulte la [guía de consola](console.md). Instalar desde código fuente no implica publicación en PyPI ni actualización de instalaciones de clientes. Respalde el estado antes de cambiar versiones y no copie credenciales o claves sintéticas a producción.
