# 从旧版 SDK 迁移

[English](../en/migration.md) · [한국어](../ko/migration.md) · [简体中文](../zh-CN/migration.md) · [日本語](../ja/migration.md) · [Español](../es/migration.md) · [Français](../fr/migration.md)

旧版嵌入式 Python SDK 及历史保留在 [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security)。本仓库是新的 Community 代理产品，不保证 SDK 兼容或自动软件包迁移。

1. 清点需保护的 HTTP/MCP 调用和目标。
2. 在 TLS 解密后部署可信签名适配器并强制流量经过代理。
3. 配置明确的工具/操作映射、限制和脱敏字段。
4. 使用合成数据观察，再验证 inline 放行、脱敏、阻断及故障行为。
5. 需要委派访问和请求绑定审批时，添加私有 Enterprise 提供程序。

现有 SDK 用户可保留固定版本，同时评估独立路由的试点。请参阅[控制台指南](console.md)。源码安装不表示已发布到 PyPI 或已升级客户部署。变更版本前备份状态，不要将合成环境的凭证或签名密钥复制到生产环境。
