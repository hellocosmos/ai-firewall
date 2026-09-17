# 真实 MCP 试点 — 0.35 Open Source Preview

[English](../en/mcp-pilot.md) · [한국어](../ko/mcp-pilot.md) · [简体中文](../zh-CN/mcp-pilot.md) · [日本語](../ja/mcp-pilot.md) · [Español](../es/mcp-pilot.md) · [Français](../fr/mcp-pilot.md)

通过现有 Envoy 检查路径连接官方 MCP Python SDK 1.30.0 客户端和文档服务器。协议与 SQLite 文档变更是真实的，数据和攻击样例是合成的。这不是客户部署认证或应用 SDK。

在仓库根目录使用 Python 3.11+ 和运行中的 Docker。每次指定新的状态目录，不覆盖已有目录。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,pilot]'
docker pull envoyproxy/envoy@sha256:57e14a549d7bd43c8d3f6d03e8cfa653e037d4b38e133acd9b54f38c524401b4
.venv/bin/python -m examples.mcp_pilot --state-dir .runtime-state/mcp-pilot-run --samples 30
```

客户端 → 本地认证签名适配器 → Envoy/AI Firewall 检查器 → MCP 文档服务器。代理不持有签名密钥。适配器令牌仅用于本地访问，不证明用户或代理身份。同一 OS 用户与回环监听不等于生产隔离；生产路由必须防止绕过。

检查初始化、工具发现、读取/修改、删除拒绝与文档保留、请求/响应邮箱脱敏和虚构 Secret 拒绝、已知恶意响应、未映射工具、未签名请求以及检查器故障时无下游执行。正文限制 64 KiB。仅验证无状态 Streamable HTTP JSON；长期 SSE、OAuth 和任意 MCP 服务器兼容性需另行验证。

**存在语义恶意指令原样通过签名检测的样例，报告标记 known_detection_miss。模型拒绝不代表防火墙检测。响应阻止发生在工具执行之后，无法撤销副作用。重复正常读取的延迟与意外拒绝不能证明总体误报率或企业容量。**

实际 LLM 需要先运行支持工具调用的本地模型，然后明确提供地址和模型名。运行器不会下载、自动选择模型或使用脚本替代。远程模型需自行配置已授权的本地隧道。

```bash
.venv/bin/python -m examples.mcp_pilot \
  --state-dir .runtime-state/mcp-agent-run --samples 30 \
  --model-url http://127.0.0.1:11434/v1 --model qwen3:1.7b
```

report.json 区分工具选择、实际结果、防火墙原因、模型错误和未执行情况，不包含原文或密钥。每项任务最多六轮模型调用、八次工具调用，不重复相同调用。退出时清理自有进程/容器，私有日志、数据库和密钥保留在状态目录。分享前审查报告。完整边界、认证环境变量和回归命令见[英文指南](../en/mcp-pilot.md)。
