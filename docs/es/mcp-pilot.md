# Piloto MCP real — candidato local 0.35

[English](../en/mcp-pilot.md) · [한국어](../ko/mcp-pilot.md) · [简体中文](../zh-CN/mcp-pilot.md) · [日本語](../ja/mcp-pilot.md) · [Español](../es/mcp-pilot.md) · [Français](../fr/mcp-pilot.md)

Conecta el cliente y servidor de documentos oficiales MCP Python SDK 1.30.0 a la inspección Envoy existente. El protocolo y los cambios SQLite son reales; los documentos y ataques son sintéticos. No es una certificación de despliegue ni un SDK de aplicación.

Ejecute desde la raíz del repositorio con Python 3.11+ y Docker activo. Use un directorio de estado nuevo en cada ejecución; no se sobrescribe uno existente.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,pilot]'
docker pull envoyproxy/envoy@sha256:57e14a549d7bd43c8d3f6d03e8cfa653e037d4b38e133acd9b54f38c524401b4
.venv/bin/python -m examples.mcp_pilot --state-dir .runtime-state/mcp-pilot-run --samples 30
```

Cliente → adaptador local autenticado que firma → Envoy/inspector AI Firewall → servidor MCP. El agente no recibe la clave de firma. El token del adaptador permite acceso local, no verifica identidad de usuario/agente. Loopback y procesos del mismo usuario no constituyen aislamiento de producción; el enrutamiento debe impedir la evasión.

Comprueba inicialización, descubrimiento, lectura/escritura, eliminación bloqueada con documento preservado, redacción de correo y rechazo de secretos ficticios en solicitudes/respuestas, respuesta maliciosa conocida, herramienta desconocida, solicitud sin firma y ausencia de ejecución durante fallo del inspector. Límite de cuerpo: 64 KiB. Solo Streamable HTTP JSON sin estado; SSE persistente, OAuth y servidores arbitrarios requieren validación propia.

**Una instrucción maliciosa semántica fuera de las firmas pasa sin cambios y se registra como known_detection_miss. Una negativa del modelo no prueba detección del firewall. Bloquear una respuesta ocurre después de ejecutar la herramienta y no revierte efectos. Las lecturas benignas repetidas no establecen una tasa general de falsos positivos ni capacidad empresarial.**

Para un LLM real, inicie primero un modelo local con llamadas a herramientas y especifique su URL y nombre. El ejecutor no descarga ni selecciona modelos y no sustituye al modelo con un guion. Para modelos remotos configure por separado un túnel local autorizado.

```bash
.venv/bin/python -m examples.mcp_pilot \
  --state-dir .runtime-state/mcp-agent-run --samples 30 \
  --model-url http://127.0.0.1:11434/v1 --model qwen3:1.7b
```

report.json distingue selección de herramientas, efectos, motivos del firewall, errores del modelo y casos no ejecutados; no incluye contenido original ni claves. Máximo seis turnos y ocho llamadas por tarea, sin repetir llamadas idénticas. Se limpian los procesos/contenedores propios; los registros, bases y claves privadas quedan en el directorio. Revise el informe antes de compartirlo. Consulte límites completos, variables de autenticación y regresiones en la [guía inglesa](../en/mcp-pilot.md).
