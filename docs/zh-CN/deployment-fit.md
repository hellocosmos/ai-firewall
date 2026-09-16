# 部署条件与提供状态

[English](../en/deployment-fit.md) · [한국어](../ko/deployment-fit.md) · [简体中文](../zh-CN/deployment-fit.md) · [日本語](../ja/deployment-fit.md) · [Español](../es/deployment-fit.md) · [Français](../fr/deployment-fit.md)

保护可通过受支持检查路径的 HTTP API 和远程 MCP 调用。保留 MCP 服务器和连接器中的现有服务认证，不替代 IAM。

Self-hosted Community 目前为源码预览版，包含基于 Docker 的代理示例。统一 Docker 安装包仍在规划中。使用相同检查基础的托管 TrapDefense Cloud 也在规划中，尚未开放注册或使用。

必须能够控制客户端地址、服务器入口或兼容的网络检查路径，并确保目标可达且无法绕过代理。SaaS 内部固定调用、本地 stdio、Shell、文件和直接数据库操作不在此 HTTP 代理范围内。

0.35 本地试点验证无状态 Streamable HTTP 的 JSON 响应。有限的 SSE 检查不代表所有流式 MCP 的兼容认证。OAuth、有状态会话和客户身份路径仍需验证。Entra 控制台 SSO 不等于 Agent IAM 或下游访问授权。

[Architecture](architecture.md) · [Delivery status](editions.md) · [MCP pilot](mcp-pilot.md)
