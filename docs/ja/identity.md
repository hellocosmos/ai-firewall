# Microsoft Entra ID — Community console SSO

[English](../en/identity.md) · [한국어](../ko/identity.md) · [简体中文](../zh-CN/identity.md) · [日本語](../ja/identity.md) · [Español](../es/identity.md) · [Français](../fr/identity.md)

Community は単一テナントの Microsoft Entra ID コンソール SSO と管理者・閲覧者ロールを提供します。コンソール認証はエージェントの実行認可ではなく、委任と承認は Enterprise の機能です。

## Configuration

単一テナントの Web アプリを登録し、以下のコールバックを正確に設定します。ユーザー用アプリロール `TrapDefense.Admin` と `TrapDefense.Viewer` を作り、エンタープライズアプリで割り当て必須を有効にしてテストユーザーを割り当てます。設定はリポジトリ外に権限 0600 で保存します。シークレットはサーバーのみに保管し、Graph 権限は不要です。

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

閲覧者はダッシュボード・イベント・ポリシー・ネットワーク・監査を閲覧でき、ログアウト以外の書き込みはサーバーで拒否します。パスワードは Entra で管理します。セッションは最長1時間で ID トークンの期限を超えません。ロール変更は次回ログイン時に反映し、既存セッションは継続再検証しません。ログアウトはローカルセッションのみ終了します。実 Entra ではローカルログインを既定で無効化します。復旧用アカウントは既定パスワード変更後に `TD_CONSOLE_LOCAL_LOGIN=1` で有効化します。コンソールはループバック専用です。合成検証は実テナント・同意・MFA・条件付きアクセスの証明ではありません。

## Protocol

Authorization code + PKCE S256, browser-bound one-time state, nonce, RS256 signature, issuer, audience, tenant and app-role validation. Tokens and client secrets are never sent to browser storage or audit logs. Synthetic mode uses an ephemeral RSA issuer with local code redemption; no Microsoft token endpoint is called. Real mode uses Microsoft authorization/token/JWKS endpoints and does not register synthetic routes.

[Microsoft authorization code flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow)
