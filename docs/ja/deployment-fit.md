# 導入条件と提供状況

> **AISG:** [接続・識別・制御・検証](aisg.md). ゲートウェイは接続キーまたは検証済みJWTを使用します。agent_keyは外部IAMなしで登録済みエージェントを識別します。JWT identity_mode: agentは検証済みテナントとエージェントのクレームを使用し、delegatedはユーザー・タスク・委任も要求します。既存エージェントは既定で委任が必要です。

[English](../en/deployment-fit.md) · [한국어](../ko/deployment-fit.md) · [简体中文](../zh-CN/deployment-fit.md) · [日本語](../ja/deployment-fit.md) · [Español](../es/deployment-fit.md) · [Français](../fr/deployment-fit.md)

対応する検査経路を通る HTTP API・リモート MCP 呼び出しを保護します。MCP サーバーとコネクターの既存認証を維持し、IAM を置き換えません。

0.42 は接続キーまたは外部 JWT のゲートウェイ認証と独立した宛先資格情報を含む Docker Compose プレビューです。イメージはソースからビルドし、TrapDefense Cloud は計画段階です。

クライアントの接続先、サーバー入口、または互換性のあるネットワーク検査経路を管理できる必要があります。接続先への到達と迂回防止が必要です。SaaS 内部の固定呼び出し、ローカル stdio、Shell、ファイル、直接 DB 操作は対象外です。

現在の証拠には実 OpenAI→合成 MCP、公式プロバイダー SDK の合成試験、実ローカル MCP/Keycloak、VS Code 初期化・検索が含まれます。モデル SSE は全体バッファ方式です。ステートフル MCP、顧客 IAM、ホスト間 HA、本番容量の認証ではありません。[0.42 検証と限界](agent-workflow.md)を参照してください。

[Architecture](architecture.md) · [Delivery status](editions.md) · [MCP pilot](mcp-pilot.md)

[Docker セルフホスティング](self-hosting.md) · [ゲートウェイ互換性](gateway-compatibility.md)
