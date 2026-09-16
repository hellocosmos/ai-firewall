# Operaciones en un mismo host — 0.34

[English](../en/operations.md) · [한국어](../ko/operations.md) · [简体中文](../zh-CN/operations.md) · [日本語](../ja/operations.md) · [Español](../es/operations.md) · [Français](../fr/operations.md)

Connections / System muestra PID, estado y reinicios. En Settings → Inspector processes, el administrador selecciona 1, 2 o 4 procesos y aplica, inicia o detiene la inspección. Viewer solo puede consultar. Detener bloquea el tráfico inline.

Los procesos comparten las bases locales de políticas, eventos y protección contra repetición. Las solicitudes nuevas leen la política guardada; las activas mantienen su versión hasta inspeccionar la respuesta. Cambiar el número reinicia el pool y Envoy. Ante un fallo se intenta restaurar; si falla la restauración, el tráfico sigue bloqueado. No se reintentan llamadas automáticamente.

Tras tres reemplazos por proceso, agotar la recuperación detiene todo el pool. Reiniciar el servicio de consola vuelve a iniciar el pool. El pool CLI independiente no lee políticas de consola y requiere reinicio completo al cambiar YAML o clave.

Requiere systemd de usuario en Linux y permisos existentes de Docker. Ejecute como usuario de instalación, sin sudo. Instalar inicia el servicio; eliminar conserva los datos. Detenga antes la consola manual.

```bash
./scripts/console-service.sh install
./scripts/console-service.sh status
./scripts/console-service.sh logs
./scripts/console-service.sh restart
./scripts/console-service.sh stop
./scripts/console-service.sh start
./scripts/console-service.sh remove
```

Habilitar el servicio no garantiza arranque desatendido: el administrador debe configurar Docker y un gestor de usuario persistente (linger). Se verificaron en un laboratorio Ubuntu 26.04 x86_64 con Python 3.12, Node 22 y Docker: instalación, reinicio real con linger, arranque automático antes de iniciar sesión SSH, restauración de dos inspectores y conservación de políticas/eventos, además de tráfico sintético permitido, bloqueado y redactado. Otros hosts y la capacidad de producción requieren validación propia. Consulte la guía inglesa sobre los grupos Docker del gestor de usuario. HA entre servidores no está implementada. No comparta SQLite en sistemas de archivos de red. Las pruebas sintéticas no certifican producción.

[English reference](../en/operations.md) · [Inspector pool](inspector-pool.md)
