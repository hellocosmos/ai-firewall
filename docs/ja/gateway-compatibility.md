# ゲートウェイクライアント互換性 — 0.37

[English](../en/gateway-compatibility.md) · [한국어](../ko/gateway-compatibility.md) · [简体中文](../zh-CN/gateway-compatibility.md) · [日本語](../ja/gateway-compatibility.md) · [Español](../es/gateway-compatibility.md) · [Français](../fr/gateway-compatibility.md)

クライアントはリモート HTTP/MCP URL を TrapDefense に変更し、接続キーヘッダーまたは OAuth Bearer JWT を使用できる必要があります。クライアント→TrapDefense と TrapDefense→宛先の認証は分離されます。

| 経路 | 0.37 の証拠 |
|---|---|
| 一般的な JSON HTTP | HTTPX による合成統合検証済み |
| 公式 Python MCP SDK 1.30.0 | 実 SDK で Streamable HTTP の初期化、通知、ツール一覧を合成統合検証済み |
| VS Code リモート MCP | 公式の `url`、`headers`、OAuth 設定と互換の構成を確認。VS Code 製品内の実行は未検証 |
| OAuth メタデータと RS256 JWT | 実 HTTP JWKS 取得と issuer/audience/time/subject/scope を合成検証済み |
| 実 Entra/Okta/Keycloak | テナント、TLS、Conditional Access、失効を別途検証する必要あり |
| ステートフル MCP、長時間 SSE、WebSocket、stdio | このプロファイルでは未対応 |

`gateway_auth` は `client_key` または `jwt` を使用します。JWT モードの TrapDefense は OAuth Resource Server として RFC 9728 メタデータと `WWW-Authenticate` を提供します。ログイン、トークン発行、DCR、refresh、OBO は外部 IdP または別の credential provider が担当します。

`target_auth` は `none`、`passthrough_bearer`、`static_bearer`、`static_api_key` に対応します。ゲートウェイ JWT は宛先へ転送されません。`passthrough_bearer` は client-key を使う旧式 HTTP 導入向けで、MCP OAuth 準拠を意味しません。

正式な互換判定前に、URL 変更、両側の認証、MCP 初期化/検出、許可・拒否、宛先副作用、PII/secret、宛先 401、検査障害、直接 URL へのフォールバックを確認してください。設定と VS Code 例は[英語ガイド](../en/gateway-compatibility.md)を参照してください。
