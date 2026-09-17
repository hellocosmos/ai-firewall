# 導入条件と提供状況

> **0.40 · AISG:** [接続・識別・制御・検証](aisg.md). ゲートウェイは接続キーまたは検証済みJWTを使用します。agent_keyは外部IAMなしで登録済みエージェントを識別します。JWT identity_mode: agentは検証済みテナントとエージェントのクレームを使用し、delegatedはユーザー・タスク・委任も要求します。既存エージェントは既定で委任が必要です。

[English](../en/deployment-fit.md) · [한국어](../ko/deployment-fit.md) · [简体中文](../zh-CN/deployment-fit.md) · [日本語](../ja/deployment-fit.md) · [Español](../es/deployment-fit.md) · [Français](../fr/deployment-fit.md)

対応する検査経路を通る HTTP API・リモート MCP 呼び出しを保護します。MCP サーバーとコネクターの既存認証を維持し、IAM を置き換えません。

0.39 は接続キーまたは外部 JWT のゲートウェイ認証と独立した宛先資格情報を含む Docker Compose プレビューです。イメージはソースからビルドし、TrapDefense Cloud は計画段階です。

クライアントの接続先、サーバー入口、または互換性のあるネットワーク検査経路を管理できる必要があります。接続先への到達と迂回防止が必要です。SaaS 内部の固定呼び出し、ローカル stdio、Shell、ファイル、直接 DB 操作は対象外です。

0.35 ローカルパイロットはステートレス Streamable HTTP の JSON 応答を検証します。制限付き SSE 検査は全ストリーミング MCP の互換性保証ではありません。OAuth、状態付きセッション、顧客の認証経路は別途検証が必要です。Entra コンソール SSO は Agent IAM や接続先の認可ではありません。

[Architecture](architecture.md) · [Delivery status](editions.md) · [MCP pilot](mcp-pilot.md)

[Docker セルフホスティング](self-hosting.md) · [ゲートウェイ互換性](gateway-compatibility.md)
