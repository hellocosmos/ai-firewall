# 部署条件与提供状态

> **AISG:** [连接、识别、控制、验证](aisg.md). 网关使用部署密钥或已验证 JWT。agent_key 无需外部 IAM 即可识别注册代理。JWT identity_mode: agent 使用已验证的租户和代理声明；delegated 还要求用户、任务和委托。现有代理默认需要委托。

[English](../en/deployment-fit.md) · [한국어](../ko/deployment-fit.md) · [简体中文](../zh-CN/deployment-fit.md) · [日本語](../ja/deployment-fit.md) · [Español](../es/deployment-fit.md) · [Français](../fr/deployment-fit.md)

保护可通过受支持检查路径的 HTTP API 和远程 MCP 调用。保留 MCP 服务器和连接器中的现有服务认证，不替代 IAM。

0.42 提供连接密钥或外部 JWT 网关认证以及独立目标凭据的 Docker Compose 预览包。镜像从源码构建，TrapDefense Cloud 仍在规划中。

必须能够控制客户端地址、服务器入口或兼容的网络检查路径，并确保目标可达且无法绕过代理。SaaS 内部固定调用、本地 stdio、Shell、文件和直接数据库操作不在此 HTTP 代理范围内。

当前证据包括真实 OpenAI 到合成 MCP 的流程、官方供应商 SDK 合成测试、本地真实 MCP/Keycloak 及 VS Code 初始化/发现。模型 SSE 完整缓冲；有状态 MCP、客户 IAM 策略、跨主机 HA 和生产容量未获认证。参见 [0.42 验证与限制](agent-workflow.md)。

[Architecture](architecture.md) · [Delivery status](editions.md) · [MCP pilot](mcp-pilot.md)

[Docker 自托管](self-hosting.md) · [网关兼容性](gateway-compatibility.md)
