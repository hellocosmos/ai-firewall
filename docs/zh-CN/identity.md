# Microsoft Entra ID — Community console SSO

[English](../en/identity.md) · [한국어](../ko/identity.md) · [简体中文](../zh-CN/identity.md) · [日本語](../ja/identity.md) · [Español](../es/identity.md) · [Français](../fr/identity.md)

Community 提供单租户 Microsoft Entra ID 控制台 SSO 及管理员、查看者角色。控制台认证不授予智能体操作权限；委派和审批属于 Enterprise。

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
