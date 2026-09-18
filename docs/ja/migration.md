# 旧 SDK からの移行

[English](../en/migration.md) · [한국어](../ko/migration.md) · [简体中文](../zh-CN/migration.md) · [日本語](../ja/migration.md) · [Español](../es/migration.md) · [Français](../fr/migration.md)

旧組み込み Python SDK と履歴は [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security) に残ります。このリポジトリはオープンソースのプロキシ製品です。SDK 互換性や自動パッケージ移行は提供しません。

1. 保護する HTTP/MCP 呼び出しと宛先を整理します。
2. クライアント HTTPS は TLS ingress で終端し、同梱の署名アダプターを使います。外部 TLS 復号装置は別途設計するネットワーク連携の選択肢で、base_url/MCP URL 構成の必須条件ではありません。
3. ツール・操作マッピング、上限、マスキング対象フィールドを明示します。
4. 合成データで観察した後、inline の許可・マスキング・遮断・障害動作を検証します。
5. エージェント別制御には登録済みローカル agent_key または明示的にマッピングした JWT と内蔵 Access Broker を使います。スコープを設定し、必要なモードでユーザー・タスク委任を加えます。

既存 SDK は固定バージョンを維持し、別経路でパイロットを評価できます。[コンソールガイド](console.md)から始めてください。ソースからのインストールは PyPI 公開や顧客環境の更新を意味しません。更新前に状態をバックアップし、合成環境の資格情報や署名鍵を本番へコピーしないでください。

## 0.38 から 0.39 の設定

0.39 は旧 `edition` キーを明示的に拒否します。Gateway-only inspector は `access_broker_enabled: false`、内蔵 Broker は `true` を使います。セルフホストでは `access_broker.enabled`、`access_broker.tenant_id`、JWT `identity_claims` が必要です。パッケージとイメージ名は `trapdefense-community` から `trapdefense-ai-firewall` に変更します。更新前に Broker JSON とコンソール状態をバックアップしてください。
