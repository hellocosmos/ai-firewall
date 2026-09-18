# 从旧版 SDK 迁移

[English](../en/migration.md) · [한국어](../ko/migration.md) · [简体中文](../zh-CN/migration.md) · [日本語](../ja/migration.md) · [Español](../es/migration.md) · [Français](../fr/migration.md)

旧版嵌入式 Python SDK 及历史保留在 [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security)。本仓库是开源代理产品，不保证 SDK 兼容或自动软件包迁移。

1. 清点需保护的 HTTP/MCP 调用和目标。
2. 在 TLS ingress 终止客户端 HTTPS，并使用内置签名适配器。外部 TLS 解密设备仅是独立网络集成的可选项，不是 base_url/MCP URL 部署的前提。
3. 配置明确的工具/操作映射、限制和脱敏字段。
4. 使用合成数据观察，再验证 inline 放行、脱敏、阻断及故障行为。
5. 按代理控制使用本地注册的 agent_key 或显式映射的 JWT 身份与内置 Access Broker。配置代理范围，仅在需要的模式下添加用户和任务委托。

现有 SDK 用户可保留固定版本，同时评估独立路由的试点。请参阅[控制台指南](console.md)。源码安装不表示已发布到 PyPI 或已升级客户部署。变更版本前备份状态，不要将合成环境的凭证或签名密钥复制到生产环境。

## 0.38 到 0.39 配置

0.39 会明确拒绝旧 `edition` 键。仅网关 inspector 使用 `access_broker_enabled: false`，内置 Broker 使用 `true`。自托管配置需要 `access_broker.enabled`、`access_broker.tenant_id` 以及 JWT `identity_claims`。包与镜像名称由 `trapdefense-community` 改为 `trapdefense-ai-firewall`。升级前请备份 Broker JSON 与控制台状态。
