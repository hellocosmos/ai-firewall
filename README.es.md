# TrapDefense — AI Firewall para agentes

[English](README.md) · [한국어](README.ko.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md)

**Inspeccione y controle acciones HTTP y MCP compatibles después del descifrado TLS.**

TrapDefense Community es un runtime de inspección proxy autoalojado con consola local. El tráfico descifrado atraviesa Envoy y el inspector para permitir, bloquear, ocultar y auditar solicitudes y respuestas. El SDK anterior permanece en [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security).

```text
AI agent → TLS decryptor → trusted signing adapter → Envoy + inspector → destination
                                                       ← response inspection ←
```

## Instalar y abrir la consola

Requiere Python 3.11+, Node.js 22.12+ o 24, npm y Docker Engine/Desktop local. Instalación desde fuentes; no implica publicación en PyPI.

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall
./scripts/install-console.sh
./scripts/run-console.sh
```

Abra [http://127.0.0.1:5176](http://127.0.0.1:5176). Inicie sesión con `admin` / `1234` y cambie la contraseña en Configuración. El idioma predeterminado es inglés. Puede elegir idioma antes o después de entrar; el navegador recuerda la selección.

## Funciones operativas

Panel y pruebas de solicitudes; política local de permiso/bloqueo y PII; escenarios HTTP sintéticos; auditoría; cambio de contraseña; interfaces, listeners y destinos; aplicación validada y reversión del contenedor Envoy propio.

Las solicitudes sintéticas recorren Envoy → inspector gRPC → destino HTTP reales. Se registran recibos del destino y ocultación de respuestas, sin sustituirlos por llamadas directas al motor. Listener predeterminado: `127.0.0.1:18082`; inspector: `18081`; destino sintético: `18090`.

## Alcance y ediciones

Community incluye política local, mapeos HTTP/MCP explícitos, firmas del salto fiable, inspección limitada de respuestas/SSE y pruebas locales depuradas. Enterprise Access Broker se distribuye aparte; Community no acredita identidad humana/de agentes ni ofrece delegación o aprobaciones.

Incluye inventario de interfaces y explicación de topología. La demo loopback no configura direcciones del SO, rutas de dos NIC, puentes transparentes ni salidas físicas. El descifrador TLS requiere un adaptador de firma fiable. Los fallos inline bloquean. Mirror de consola observa su ruta síncrona; el colector mirror separado no bloquea originales.

## Documentación y verificación

[Guía de consola](docs/es/console.md) · [Architecture](docs/es/architecture.md) · [Community / Enterprise](docs/es/editions.md) · [SDK → Proxy](docs/es/migration.md) · [Security](docs/es/security.md)

El código de aplicación está en inglés y mantiene seis diccionarios UI completos. Los casos de seguridad en otros idiomas prueban entradas internacionales. Cada guía tiene un selector de idioma al principio.

```bash
.venv/bin/python -m pytest -q
npm run check --prefix console
npm run build --prefix console
# Stop the running console before this Docker test.
TD_CONSOLE_E2E=1 .venv/bin/python -m pytest tests/test_console.py -q
```

Son pruebas sintéticas locales, no certificación de TLS/IdP del cliente, rutas forzadas de producción, HA o rendimiento. La detección tiene falsos positivos/negativos; la auditoría local no es inmutable.

## License

Community usa MIT. No incluye código privado Enterprise ni activos de clientes.
