# Real MCP pilot — 0.35 Open Source Preview

[English](../en/mcp-pilot.md) · [한국어](../ko/mcp-pilot.md) · [简体中文](../zh-CN/mcp-pilot.md) · [日本語](../ja/mcp-pilot.md) · [Español](../es/mcp-pilot.md) · [Français](../fr/mcp-pilot.md)

This optional source example connects the official MCP Python client to real document tools through TrapDefense. The wire protocol, Envoy forwarding, inspector and SQLite document mutations are real; the documents and attack fixtures are synthetic. It is not a customer deployment or an application SDK.

## Run the protocol pilot

From the repository root, with Python 3.11+, Docker running and access to its daemon:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,pilot]'
docker pull envoyproxy/envoy@sha256:57e14a549d7bd43c8d3f6d03e8cfa653e037d4b38e133acd9b54f38c524401b4
.venv/bin/python -m examples.mcp_pilot --state-dir .runtime-state/mcp-pilot-run --samples 30
```

Use a **new** state directory for each run; an existing directory is never overwritten. MCP `1.30.0` is pinned to the maintained v1 SDK interface. This example uses stateless Streamable HTTP with JSON responses: initialize, initialized notification, tool discovery and tool calls. Stateful sessions, long-lived SSE, OAuth and arbitrary third-party MCP servers are not certified by it. See the [official SDK v1 documentation](https://py.sdk.modelcontextprotocol.io/v1/).

The command allocates available ports, starts only its own processes/container, prints sanitized JSON and saves `report.json` in the private state directory. It cleans up those processes/container when finished. Infrastructure or protocol failure exits 1 without a success report; private logs remain for diagnosis. Model errors or exhausted budgets save the partial report and exit 2. A model finishing does not imply task success: inspect task_success and target_exercised. No console service or existing policy is changed. Linux uses Docker host networking with loopback listeners; macOS uses Docker Desktop host access and a loopback-published proxy port.

## What crosses the firewall

```text
Official MCP client / optional LLM agent
  -> authenticated local pilot adapter (owns the signing key)
  -> Envoy -> existing AI Firewall inspector
  -> official MCP document server -> finite SQLite documents
```

The adapter preserves request bytes, strips caller-supplied reserved forwarding context and signs a fresh request for one fixed destination. Its bearer token is local pilot access, **not** verified agent/user identity. The agent client never reads the attestation key. Same-user processes and loopback listeners are not a production isolation boundary: an operator can reach the baseline/upstream directly. Production routing must prevent bypass. This example does not implement TLS decryption or network steering.

The server exposes only `read_document`, `write_document` and `delete_document` on a finite test document set. It has no arbitrary file, shell or outbound network tool. The control methods and document actions are explicitly mapped. Request blocking is checked against unchanged database state and zero downstream executions, not merely an HTTP error. A separate direct-baseline database demonstrates the effect of removing the firewall.

## Evidence and limitations

The deterministic suite checks:

- Official SDK initialization, discovery, successful document reads and a persisted update.
- Denied deletion with the protected document retained; the direct baseline can delete its own copy.
- Request and response email redaction, confirmed from actual stored/client content.
- Request/response dummy secret rejection and a known malicious tool-response signature.
- Unknown tool and unsigned proxy-request rejection; an inspector outage prevents downstream execution.
- Sanitized audit without the fixture email or dummy secret.
- Equal sequential benign read samples, with initialization/warmup and LLM inference excluded from latency.

**A semantic malicious instruction outside the current signatures passes unchanged.** The report deliberately records `known_detection_miss`; a passing test suite does not mean universal prompt-injection protection. A model declining that instruction is model behavior, not evidence that the firewall detected it. Response blocking occurs after a tool executed and cannot undo its side effects. The deny policy still prevents the mapped deletion action regardless of phrasing.

The latency report describes this small local workload only. Repeated benign reads do not establish a general false-positive rate, concurrency capacity or enterprise sizing. Request/response bodies are limited to 64 KiB in this pilot. Local logs/databases/signing state are private and are not a shareable report; publish only reviewed sanitized `report.json`.

## Add a real local LLM agent

Provide a running OpenAI-compatible local chat-completions endpoint with a tool-capable model. The runner does not download/select a model or silently substitute scripted actions. Synthetic document output is sent only to the explicitly selected loopback endpoint. To use a separately hosted model, establish an authorized local tunnel yourself.

```bash
.venv/bin/python -m examples.mcp_pilot \
  --state-dir .runtime-state/mcp-agent-run --samples 30 \
  --model-url http://127.0.0.1:11434/v1 --model qwen3:1.7b
```

If that local endpoint requires authentication, use `TD_PILOT_MODEL_API_KEY` in the process environment; never add a key to commands, configuration committed to Git, or the report. No API key is needed for the ordinary local Ollama endpoint.

The LLM discovers tools and chooses calls for a normal read/update task, a denied deletion, a known malicious response and a semantic injection fixture. The report distinguishes actual tool selections, model errors/step limits, downstream effects and firewall reasons. There are at most six model turns and eight tool calls per task; identical calls are not replayed. No raw model transcript or document body is included in the report. Model performance and security remain separate from the deterministic protocol evidence.

## Regression checks

```bash
.venv/bin/python -m pytest tests/test_mcp_pilot.py -q
TD_MCP_PILOT=1 .venv/bin/python -m pytest tests/runtime/test_mcp_pilot_runtime.py -q
```

The optional tests skip when MCP is not installed; the Docker test also requires `TD_MCP_PILOT=1`. The normal open-source installation remains independent of MCP SDK dependencies. The existing CI proxy job installs the pilot extra and runs the real MCP regression when this change is published.
