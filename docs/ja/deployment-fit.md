# 導入条件と提供状況

[English](../en/deployment-fit.md) · [한국어](../ko/deployment-fit.md) · [简体中文](../zh-CN/deployment-fit.md) · [日本語](../ja/deployment-fit.md) · [Español](../es/deployment-fit.md) · [Français](../fr/deployment-fit.md)

対応する検査経路を通る HTTP API・リモート MCP 呼び出しを保護します。MCP サーバーとコネクターの既存認証を維持し、IAM を置き換えません。

Self-hosted Community は Docker プロキシの例を含むソースベースのプレビューです。統合 Docker インストールパッケージは計画段階です。同じ検査基盤を使うマネージド TrapDefense Cloud も計画段階で、登録・利用はまだできません。

クライアントの接続先、サーバー入口、または互換性のあるネットワーク検査経路を管理できる必要があります。接続先への到達と迂回防止が必要です。SaaS 内部の固定呼び出し、ローカル stdio、Shell、ファイル、直接 DB 操作は対象外です。

0.35 ローカルパイロットはステートレス Streamable HTTP の JSON 応答を検証します。制限付き SSE 検査は全ストリーミング MCP の互換性保証ではありません。OAuth、状態付きセッション、顧客の認証経路は別途検証が必要です。Entra コンソール SSO は Agent IAM や接続先の認可ではありません。

[Architecture](architecture.md) · [Delivery status](editions.md) · [MCP pilot](mcp-pilot.md)
