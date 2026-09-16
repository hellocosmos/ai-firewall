# Grupo de inspectores Community

[English](../en/inspector-pool.md) · [한국어](../ko/inspector-pool.md) · [简体中文](../zh-CN/inspector-pool.md) · [日本語](../ja/inspector-pool.md) · [Español](../es/inspector-pool.md) · [Français](../fr/inspector-pool.md)

Ejecuta 1, 2 o 4 inspectores en el mismo servidor y genera la configuración de Envoy. No inicia Docker ni sustituye la consola. Enterprise y HA entre servidores quedan fuera del alcance.

Todos los procesos comparten la misma base local antirrepetición y el registro de auditoría. No use bases separadas ni sistemas de archivos de red. Las rutas relativas parten del directorio de inicio. La política y la clave se fijan en una copia privada al arrancar; los cambios requieren reiniciar todo el grupo y coordinar Envoy y el emisor de firmas.

Cada proceso admite por defecto hasta 3 reinicios. Agotado el límite, se detiene todo el grupo. Las solicitudes fallidas no se reenvían automáticamente. Si fallan todos los inspectores, el tráfico no evita la inspección.

status.json incluye estado, PID, puertos y reinicios. El directorio exige permisos 0700 y la clave acceso exclusivo del propietario. Al terminar forzosamente el supervisor, los hijos también terminan, pero pueden quedar archivos de estado y copias privadas; compruebe PID, fecha y salud real.

Los puertos iniciales son 18101 para gRPC, 18111 para salud y 18082 para el proxy. Docker Desktop requiere los argumentos adicionales siguientes y publicación solo en loopback. Linux usa los valores predeterminados con host network. La integración con la UI y el gestor de servicios no está incluida.

```bash
.venv/bin/trapdefense-inspector-pool \
  --config "$PWD/.runtime-state/pool-demo/inspector.yaml" \
  --key-file "$PWD/.runtime-state/pool-demo/attestation.key" \
  --state-directory "$PWD/.runtime-state/pool-supervisor" \
  --envoy-output "$PWD/.runtime-state/pool-envoy.yaml" \
  --replicas 2
```

```text
--proxy-bind 0.0.0.0 --inspector-address host.docker.internal --upstream-address host.docker.internal
```

[Complete setup and limits / English](../en/inspector-pool.md)
