# Docker 自托管 — 0.36 Community Preview

[English](../en/self-hosting.md) · [한국어](../ko/self-hosting.md) · [简体中文](../zh-CN/self-hosting.md) · [日本語](../ja/self-hosting.md) · [Español](../es/self-hosting.md) · [Français](../fr/self-hosting.md)

0.36 提供同时运行适配器、Envoy、检查器和管理界面的 Docker Compose 预览包。镜像从源码本地构建。TrapDefense Cloud 仍在规划中，尚未开放注册。

客户端必须允许修改 MCP/API URL 并添加 `X-TD-Client-Key` 请求头。每个部署只有一个固定目标，并显式映射路由和工具。无法修改这些设置的客户端不能直接接入。

| 类型 | 支持范围 |
|---|---|
| HTTP API | JSON、精确 method/path、最大 1 MiB、有界响应 |
| MCP | 无状态 JSON POST、显式映射的控制方法和工具 |
| 目标认证 | 透传已有 Bearer/API Key，或注入服务器文件中的固定 Bearer |
| 不支持 | OAuth 登录代理和令牌交换、Cookie/会话、长连接 SSE、WebSocket、stdio、封闭 SaaS 内部调用 |

管理员密码用于控制台登录；连接密钥用于访问 TrapDefense，不证明代理身份；服务令牌由目标服务验证权限。透传预先获取的 OAuth 令牌不等于代理 OAuth 登录。Entra 控制台 SSO 是已有源码控制台功能，未接入此 Docker 配置。

## Docker

需要 Git 和 Docker Compose v2。init 要求设置至少 12 个字符的管理员密码，没有默认密码。示例配置指向合成目标，不代表真实服务集成。

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall/deploy/selfhost
docker compose build app
docker compose run --rm app init
docker compose --profile smoke up -d
docker compose run --rm app client-key
```

在 `http://localhost:18080` 以 admin 登录。使用 client-key 命令读取连接密钥，并存入客户端的机密请求头配置。网关为 `http://localhost:18084`；合成目标令牌为 `Bearer synthetic-target-token`。

连接真实服务时修改 deployment.yaml 中的 upstream、authority、路径、工具和 resource。HTTPS 验证证书；仅在可信网络上显式允许 HTTP。passthrough 保留服务认证头。static_bearer 需要 UID 10001 可读、0600 权限的密钥文件；输入 Authorization 会被拒绝。共享连接密钥的用户使用同一服务账户权限。

UI 管理策略和密码。变更映射时，先备份，再运行 policy-reset、render 并重建服务。此操作仅重置已保存策略，保留账户、密钥和事件。新请求使用新策略。

默认端口只绑定回环地址。远程访问需要 TLS 反向代理和准确的 console_origin。检查器和 Envoy 不公开主机端口。客户需通过网络控制防止绕过。

重启保留命名卷中的状态。停止后备份两个卷及配置。down -v 会删除数据；回滚需旧镜像及对应备份。监听器健康不能证明认证或检查成功，请验证允许、阻止及目标副作用。长连接、HA 和真实客户 IAM 需单独验证。

[Detailed examples, backup and migration (English)](../en/self-hosting.md)
