# Microsoft Entra ID — TrapDefense console SSO

**安装路径：**Docker 部署请遵循[自托管指南](self-hosting.md)。独立源码控制台的 Entra SSO 和合成演示配置不会自动应用到 Docker。

> **AISG:** [连接、识别、控制、验证](aisg.md). 网关使用部署密钥或已验证 JWT。agent_key 无需外部 IAM 即可识别注册代理。JWT identity_mode: agent 使用已验证的租户和代理声明；delegated 还要求用户、任务和委托。现有代理默认需要委托。

[English](../en/identity.md) · [한국어](../ko/identity.md) · [简体中文](../zh-CN/identity.md) · [日本語](../ja/identity.md) · [Español](../es/identity.md) · [Français](../fr/identity.md)

控制台支持单租户 Microsoft Entra ID SSO 以及管理员、查看者角色。控制台操作员身份与智能体授权是独立边界；智能体授权由内置 Access Broker 执行。

## Configuration

注册单租户 Web 应用并准确配置下方回调地址。创建用户应用角色 `TrapDefense.Admin` 和 `TrapDefense.Viewer`，在企业应用中启用分配要求并分配测试用户。配置文件保存在仓库外，权限设为 0600。密钥仅存于服务器，无需 Graph 权限。

```json
{
  "tenant_id": "YOUR-TENANT-UUID",
  "client_id": "YOUR-APPLICATION-UUID",
  "client_secret": "YOUR-SERVER-SIDE-SECRET",
  "redirect_uri": "http://localhost:5176/demo-api/auth/callback"
}
```

```bash
chmod 600 /absolute/path/entra.json
TD_ENTRA_CONFIG=/absolute/path/entra.json ./scripts/run-console.sh
```

## Synthetic demo

```bash
TD_SYNTHETIC_ENTRA=1 ./scripts/run-console.sh
```

`http://127.0.0.1:5176` → **Sign in with Synthetic Entra** → **Admin / Viewer**.

查看者可读取仪表盘、事件、策略、网络和审计；除退出外的写入均由服务器拒绝。Entra 用户在 Entra 管理密码。会话最长一小时且不超过 ID 令牌有效期。角色变更在下次登录生效，不持续重新验证现有会话。退出仅结束本地会话。真实 Entra 默认禁用本地登录；修改默认密码后可用 `TD_CONSOLE_LOCAL_LOGIN=1` 启用恢复账户。控制台仅监听回环地址。合成成功不代表真实租户、同意、MFA 或条件访问验证。

## Protocol

Authorization code + PKCE S256, browser-bound one-time state, nonce, RS256 signature, issuer, audience, tenant and app-role validation. Tokens and client secrets are never sent to browser storage or audit logs. Synthetic mode uses an ephemeral RSA issuer with local code redemption; no Microsoft token endpoint is called. Real mode uses Microsoft authorization/token/JWKS endpoints and does not register synthetic routes.

[Microsoft authorization code flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow)

## 智能体 JWT identity mapping

以下说明 **delegated JWT 模式**。本地 agent_key 和自主 agent 模式请参见 [AISG 指南](aisg.md)。

Broker 模式先验证外部 IdP JWT 的 issuer、audience 与 scope，再仅将 `identity_claims` 中显式配置的值映射为 tenant、user、agent、delegation 与 task 身份。任意 claims 与 gateway token 不会进入检查证据或目标服务。缺少必需 claim 或 tenant 不匹配时会 fail closed。可使用 Entra、Okta、Keycloak 等兼容 issuer，但客户必须验证 claim 签发与 workload 绑定的可信度。[自托管](self-hosting.md) · [安全](security.md)
