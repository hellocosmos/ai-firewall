# TrapDefense — 面向智能体的 AI 防火墙

[English](README.md) · [한국어](README.ko.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md)

> **Community Preview：** 适用于本地评估和集成工作。生产流量、高可用、容量和客户身份路径需要单独验证。

**控制从提示词到真实操作的完整路径。**

TrapDefense Community 是带本地运维界面的自托管 AI 防火墙。检查受支持的 HTTP 和 MCP 工具调用，执行操作策略，对敏感数据脱敏并记录决策证据。旧 SDK 保留在 [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security)。

```text
AI agents → TrapDefense AI Firewall → Tools / MCP servers / APIs
            Action policy · Data protection · Audit
          ← Inspected responses ←
```

这是产品的逻辑流程。可信转发、流量可见性和强制路由要求请参阅[部署架构](docs/zh-CN/architecture.md)。

Community 提供单租户 Microsoft Entra ID 控制台 SSO 及管理员、查看者角色。控制台认证不授予智能体操作权限；委派和审批属于 Enterprise。 [Entra SSO](docs/zh-CN/identity.md).

## Docker 自托管 · 0.36

[Docker 自托管: integration contract, installation and verification](docs/zh-CN/self-hosting.md)


## 部署条件与提供状态

保护可通过受支持检查路径的 HTTP API 和远程 MCP 调用。保留 MCP 服务器和连接器中的现有服务认证，不替代 IAM。

0.36 提供同时运行适配器、Envoy、检查器和管理界面的 Docker Compose 预览包。镜像从源码本地构建。TrapDefense Cloud 仍在规划中，尚未开放注册。

[交付与兼容性](docs/zh-CN/deployment-fit.md)

## TrapDefense 的差异

TrapDefense 控制模型输出转化为真实操作的边界，将基于代理的执行点、本地数据保护和明确的身份语义结合在同一运行路径中。

| 边界 | TrapDefense 明确保障的内容 |
|---|---|
| **独立执行点** | 受支持的 HTTP 和 MCP 调用在到达配置目标之前经过 Envoy 和检查器，无需在应用中嵌入旧 SDK。部署路由必须防止绕过。 |
| **双向数据控制** | 对完整且有界的请求与响应（包括受支持的 SSE）应用操作、PII 和 Secret 策略，执行放行、阻断或脱敏。 |
| **明确的身份边界** | Community Entra ID SSO 认证控制台操作员；独立的 Enterprise 试点综合评估用户、智能体、委派、任务、资源和操作。 |
| **明确的故障语义** | Inline 检查失败时关闭放行。Mirror 仅记录 `would_*` 假设结果，不修改原始流量或审批状态。 |
| **可运营的证据** | 本地控制台展示决策、策略覆盖、目标回执和净化证据，且不会把受保护原文复制到审计记录。 |

## 五分钟本地评估

需要 Python 3.11+、Node.js 22.12+ 或 24、npm 和本地 Docker Engine/Desktop。采用源码安装，不表示已发布到 PyPI。

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall
./scripts/install-console.sh
./scripts/run-console.sh
```

打开 [http://127.0.0.1:5176](http://127.0.0.1:5176)，以 `admin` / `1234` 登录，然后在设置中修改密码。默认语言为英语；登录前后均可选择语言，浏览器会保存选择。

## 运维功能

仪表板、请求证据、本地放行/阻断策略、全局/路由/工具 PII 策略及 Mirror `would_*` 评估、合成 HTTP 场景、审计、密码修改、接口清单、监听/上游设置，以及所拥有 Envoy 容器的验证、应用与回滚。

合成请求经过真实 Envoy → gRPC 检查器 → HTTP 目标路径，记录目标回执和响应脱敏，不以直接调用引擎代替。默认监听 `127.0.0.1:18082`，检查器使用 `18101–18104`，合成目标使用 `18090`。

## 范围与版本

Community 包含本地策略、显式 HTTP/MCP 映射、可信跳签名、有界响应/SSE 检查及净化本地证据。Enterprise Access Broker 是单独分发的私有试点；Community 控制台 SSO 不授予智能体身份、委派访问或审批。

提供 NIC 清单和拓扑说明。回环演示不配置系统地址、双网卡路由、透明桥或物理出口。inline 检查失败时阻断。控制台 Mirror 观察同步路径；独立 mirror 收集器不能阻断原始流量。

## 本地性能基线

停止控制台，然后通过同一 Envoy → gRPC 检查器 → 合成 HTTP 路径执行顺序测量。

```bash
.venv/bin/trapdefense-benchmark --scenario read --iterations 30
```

JSON 中的 p50/p95 延迟和结果计数只用于本地回归比较，不代表生产吞吐量或容量。参见[基准测试](docs/zh-CN/benchmark.md)。

## 文档与验证

[控制台指南](docs/zh-CN/console.md) · [Architecture](docs/zh-CN/architecture.md) · [Community / Enterprise](docs/zh-CN/editions.md) · [基准测试](docs/zh-CN/benchmark.md) · [SDK → Proxy](docs/zh-CN/migration.md) · [Security](docs/zh-CN/security.md)

应用源码使用英语，并维护六套完整 UI 字典。离线 PII 检查支持英语、韩语、简体中文、日语、西班牙语和法语的显式模式与校验器；不提供覆盖姓名、位置和地址的通用 NER。每份本地化指南顶部均可切换语言。

确定性的 Secret 检查会在受支持的正文、响应和 SSE 中阻止已识别的服务商令牌、签名 JWT、Azure Storage SAS 链接和敏感字段中的高熵凭证。请求凭证头仅传给已完成签名验证的映射目标，并从审计证据中排除。具体范围和限制请参阅 [Security](docs/zh-CN/security.md)。

```bash
.venv/bin/python -m pytest -q
npm run check --prefix console
npm run build --prefix console
# Stop the running console before this Docker test.
TD_CONSOLE_E2E=1 .venv/bin/python -m pytest tests/test_console.py -q
```

这些是本地合成验证，不代表客户 TLS/IdP 集成、生产强制路由、HA 或性能认证。检测有误报/漏报；本地审计不是不可变存储。

## License

Community 采用 MIT 许可，不包含私有 Enterprise 代码和客户资产。


## 同一主机运维 — 0.34

在 Connections / System 查看 PID、状态和重启次数。管理员可在 Settings → Inspector processes 选择 1、2 或 4 个进程并应用、启动或停止。Viewer 仅可查看。停止期间阻止内联流量。

[Operations](docs/zh-CN/operations.md) · [Inspector pool](docs/zh-CN/inspector-pool.md)

## 真实 MCP 试点（0.35 Community Preview）

通过防火墙运行真实 MCP 初始化、发现和文档工具，可选连接本地 LLM。明确区分合成数据、检测边界与直接/代理延迟。

[MCP pilot](docs/zh-CN/mcp-pilot.md)
