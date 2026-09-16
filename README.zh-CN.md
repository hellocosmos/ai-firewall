# TrapDefense — 面向智能体的 AI 防火墙

[English](README.md) · [한국어](README.ko.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md)

**在 TLS 解密后检查并控制受支持的 HTTP 和 MCP 操作。**

TrapDefense Community 是带本地运维界面的自托管代理检查运行时。解密流量通过 Envoy 和检查器，实现请求/响应放行、阻断、脱敏和审计。旧 SDK 保留在 [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security)。

```text
AI agent → TLS decryptor → trusted signing adapter → Envoy + inspector → destination
                                                       ← response inspection ←
```

## 安装并打开控制台

需要 Python 3.11+、Node.js 22.12+ 或 24、npm 和本地 Docker Engine/Desktop。采用源码安装，不表示已发布到 PyPI。

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall
./scripts/install-console.sh
./scripts/run-console.sh
```

打开 [http://127.0.0.1:5176](http://127.0.0.1:5176)，以 `admin` / `1234` 登录，然后在设置中修改密码。默认语言为英语；登录前后均可选择语言，浏览器会保存选择。

## 运维功能

仪表板、请求证据、本地放行/阻断与 PII 策略、合成 HTTP 场景、审计、密码修改、接口清单、监听/上游设置，以及所拥有 Envoy 容器的验证、应用与回滚。

合成请求经过真实 Envoy → gRPC 检查器 → HTTP 目标路径，记录目标回执和响应脱敏，不以直接调用引擎代替。默认监听 `127.0.0.1:18082`，检查器使用 `18081`，合成目标使用 `18090`。

## 范围与版本

Community 包含本地策略、显式 HTTP/MCP 映射、可信跳签名、有界响应/SSE 检查及净化本地证据。Enterprise Access Broker 实现单独分发；Community 不提供用户/代理身份、委派访问或审批。

提供 NIC 清单和拓扑说明。回环演示不配置系统地址、双网卡路由、透明桥或物理出口。TLS 解密器需要可信签名适配器。inline 检查失败时阻断。控制台 Mirror 观察同步路径；独立 mirror 收集器不能阻断原始流量。

## 文档与验证

[控制台指南](docs/zh-CN/console.md) · [Architecture](docs/zh-CN/architecture.md) · [Community / Enterprise](docs/zh-CN/editions.md) · [SDK → Proxy](docs/zh-CN/migration.md) · [Security](docs/zh-CN/security.md)

应用源码使用英语，维护六套完整 UI 字典。非英语安全测试样本用于验证国际化输入。每份本地化指南顶部均可切换语言。

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
