# TrapDefense — AI Firewall para agentes

[English](README.md) · [한국어](README.ko.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md)

> **Community Preview:** apto para evaluación local e integración. El tráfico de producción, HA, capacidad y rutas de identidad del cliente requieren validación aparte.

**Controle toda la ruta desde el prompt hasta la acción.**

TrapDefense Community es un AI Firewall autoalojado con consola local. Inspeccione llamadas HTTP y MCP compatibles, aplique políticas de acción, oculte datos sensibles y conserve evidencias de las decisiones. El SDK anterior permanece en [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security).

```text
AI agents → TrapDefense AI Firewall → Tools / MCP servers / APIs
            Action policy · Data protection · Audit
          ← Inspected responses ←
```

Flujo lógico del producto. Consulte la [arquitectura de despliegue](docs/es/architecture.md) para los requisitos de reenvío de confianza, visibilidad del tráfico y enrutamiento.

Community incluye SSO de consola Microsoft Entra ID de un solo tenant, con roles Administrador y Lector. La autenticación de consola no autoriza acciones de agentes; delegación y aprobación siguen en Enterprise. [Entra SSO](docs/es/identity.md).

## Compatibilidad y disponibilidad

Proteja llamadas HTTP API y MCP remoto que pueda dirigir por una ruta de inspección compatible. Mantenga la autenticación existente en servidores MCP y conectores; no sustituya su IAM.

Self-hosted Community es una versión preliminar desde el código fuente con ejemplos de proxy en Docker. El paquete Docker integrado está previsto. TrapDefense Cloud también está previsto, con la misma base de inspección; todavía no admite registros ni está disponible.

[Entrega y compatibilidad](docs/es/deployment-fit.md)

## Por qué TrapDefense

TrapDefense gobierna el punto en que la salida del modelo se convierte en una acción real. Combina un punto de aplicación basado en proxy, protección local de datos y límites de identidad explícitos.

| Límite | Lo que TrapDefense hace explícito |
|---|---|
| **Punto de aplicación independiente** | Las llamadas HTTP y MCP compatibles atraviesan Envoy y el inspector antes de llegar al destino configurado. La aplicación no necesita incorporar el SDK anterior. El despliegue debe impedir rutas alternativas. |
| **Control bidireccional de datos** | Las solicitudes y respuestas completas y acotadas, incluido SSE compatible, pueden permitirse, bloquearse o redactarse mediante políticas de acción, PII y secretos. |
| **Límite de identidad explícito** | Entra ID SSO de Community autentica al operador de consola. El piloto Enterprise separado evalúa usuario, agente, delegación, tarea, recurso y acción. |
| **Semántica de fallo clara** | Inline bloquea cuando la inspección falla. Mirror registra resultados hipotéticos `would_*` sin cambiar el tráfico original ni el estado de aprobación. |
| **Evidencia operativa** | La consola local muestra decisiones, cobertura de políticas, recibos del destino y evidencia saneada sin copiar contenido protegido al registro de auditoría. |

## Evaluación local en cinco minutos

Requiere Python 3.11+, Node.js 22.12+ o 24, npm y Docker Engine/Desktop local. Instalación desde fuentes; no implica publicación en PyPI.

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall
./scripts/install-console.sh
./scripts/run-console.sh
```

Abra [http://127.0.0.1:5176](http://127.0.0.1:5176). Inicie sesión con `admin` / `1234` y cambie la contraseña en Configuración. El idioma predeterminado es inglés. Puede elegir idioma antes o después de entrar; el navegador recuerda la selección.

El resultado correcto muestra proxy, inspector y destino listos en **Conexiones / Sistema**; **Leer notas de negocio** debe producir HTTP 200 y un recibo del destino. La contraseña inicial es solo para la demo loopback y debe cambiarse de inmediato. Este flujo no configura un servicio público, rutas de producción ni un destino empresarial real.

## Funciones operativas

Panel y pruebas de solicitudes; política local de permiso/bloqueo; política PII global, por ruta y por herramienta con evaluación Mirror `would_*`; escenarios HTTP sintéticos; auditoría; cambio de contraseña; interfaces, listeners y destinos; aplicación validada y reversión del contenedor Envoy propio.

Las solicitudes sintéticas recorren Envoy → inspector gRPC → destino HTTP reales. Se registran recibos del destino y ocultación de respuestas, sin sustituirlos por llamadas directas al motor. Listener predeterminado: `127.0.0.1:18082`; inspector: `18101–18104`; destino sintético: `18090`.

## Alcance y ediciones

Community incluye política local, mapeos HTTP/MCP explícitos, firmas del salto fiable, inspección limitada de respuestas/SSE y pruebas locales depuradas. Enterprise Access Broker es un piloto privado distribuido aparte; el SSO de consola Community no acredita identidad de agentes ni ofrece delegación o aprobaciones.

Incluye inventario de interfaces y explicación de topología. La demo loopback no configura direcciones del SO, rutas de dos NIC, puentes transparentes ni salidas físicas. Los fallos inline bloquean. Mirror de consola observa su ruta síncrona; el colector mirror separado no bloquea originales.

## Línea base de rendimiento local

Detenga la consola y mida secuencialmente la misma ruta Envoy → inspector gRPC → destino HTTP sintético.

```bash
.venv/bin/trapdefense-benchmark --scenario read --iterations 30
```

La latencia p50/p95 y los recuentos del JSON sirven para regresión local, no acreditan rendimiento ni capacidad de producción. Consulte [Benchmarking](docs/es/benchmark.md).

## Documentación y verificación

[Guía de consola](docs/es/console.md) · [Architecture](docs/es/architecture.md) · [Community / Enterprise](docs/es/editions.md) · [Benchmarking](docs/es/benchmark.md) · [SDK → Proxy](docs/es/migration.md) · [Security](docs/es/security.md)

El código de aplicación está en inglés y mantiene seis diccionarios UI completos. La inspección PII sin conexión admite patrones y validadores explícitos en inglés, coreano, chino simplificado, japonés, español y francés. No ofrece NER general de nombres, ubicaciones o direcciones. Cada guía tiene un selector de idioma al principio.

La inspección determinista de secretos bloquea tokens de proveedores reconocidos, JWT firmados, enlaces SAS de Azure Storage y credenciales de alta entropía en campos sensibles de cuerpos, respuestas y SSE compatibles. Las cabeceras de credenciales solo llegan al destino asignado y verificado por firma, y se excluyen de la auditoría. Consulte [Security](docs/es/security.md) para conocer alcance y límites.

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


## Operaciones en un mismo host — 0.34

Connections / System muestra PID, estado y reinicios. En Settings → Inspector processes, el administrador selecciona 1, 2 o 4 procesos y aplica, inicia o detiene la inspección. Viewer solo puede consultar. Detener bloquea el tráfico inline.

[Operations](docs/es/operations.md) · [Inspector pool](docs/es/inspector-pool.md)

## Piloto MCP real (candidato local 0.35)

Ejecute inicialización, descubrimiento y herramientas documentales MCP reales a través del firewall, con un agente LLM local opcional. Datos sintéticos, límites explícitos y latencia directa/proxy.

[MCP pilot](docs/es/mcp-pilot.md)
