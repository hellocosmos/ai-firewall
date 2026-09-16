# 网关客户端兼容性 — 0.37

[English](../en/gateway-compatibility.md) · [한국어](../ko/gateway-compatibility.md) · [简体中文](../zh-CN/gateway-compatibility.md) · [日本語](../ja/gateway-compatibility.md) · [Español](../es/gateway-compatibility.md) · [Français](../fr/gateway-compatibility.md)

客户端必须能把远程 HTTP/MCP URL 改为 TrapDefense，并使用连接密钥请求头或 OAuth Bearer JWT。客户端到 TrapDefense 的认证与 TrapDefense 到目标的认证彼此独立。

| 路径 | 0.37 证据 |
|---|---|
| 通用 JSON HTTP | 已完成 HTTPX 合成集成验证 |
| 官方 Python MCP SDK 1.30.0 | 已用真实 SDK 完成 Streamable HTTP 初始化、通知和工具列表的合成集成验证 |
| VS Code 远程 MCP | 配置与官方 `url`、`headers` 和 OAuth 字段兼容；尚未在 VS Code 产品内执行验证 |
| OAuth 元数据与 RS256 JWT | 已验证真实 HTTP JWKS 获取及 issuer/audience/time/subject/scope；属于合成证据 |
| 真实 Entra/Okta/Keycloak | 仍需验证租户、TLS、Conditional Access 和吊销行为 |
| 有状态 MCP、长连接 SSE、WebSocket、stdio | 本配置不支持 |

`gateway_auth` 支持 `client_key` 或 `jwt`。JWT 模式下，TrapDefense 是 OAuth Resource Server，发布 RFC 9728 元数据并返回 `WWW-Authenticate`。登录、令牌签发、DCR、刷新和 OBO 由外部 IdP 或独立凭据提供方负责。

`target_auth` 支持 `none`、`passthrough_bearer`、`static_bearer` 和 `static_api_key`。网关 JWT 不会传给目标。`passthrough_bearer` 仅用于基于 client-key 的旧式 HTTP 接入，不代表符合 MCP OAuth。

正式确认兼容前，请验证 URL 替换、双向认证、MCP 初始化/发现、允许与拒绝、目标副作用、PII/secret、目标 401、检查链路故障以及是否回退到直连 URL。配置和 VS Code 示例见[英文指南](../en/gateway-compatibility.md)。
