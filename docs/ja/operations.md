# 同一ホストの運用 — 0.34

[English](../en/operations.md) · [한국어](../ko/operations.md) · [简体中文](../zh-CN/operations.md) · [日本語](../ja/operations.md) · [Español](../es/operations.md) · [Français](../fr/operations.md)

Connections / System で PID、状態、再起動回数を確認します。管理者は Settings → Inspector processes で 1・2・4 プロセスを選び、適用・開始・停止できます。Viewer は閲覧のみです。停止中はインライン通信を遮断します。

ワーカーはローカルのポリシー、イベント、リプレイ防止DBを共有します。新しい要求は保存済みポリシーを読み、処理中の要求は応答検査まで元のポリシーを保持します。台数変更時はプールと Envoy を一時停止し、失敗時は復元を試みます。復元できない場合は遮断を維持します。ツール要求を自動再試行しません。

子プロセスごとに最大3回の復旧を行い、上限を超えるとプール全体を停止します。コンソールサービスの再起動でプールも起動します。独立CLIプールはコンソールのポリシーを読みません。YAML・鍵の変更後は全体の再起動が必要です。

Linux のユーザー systemd と既存の Docker 権限が必要です。sudo を使わずインストールユーザーで実行します。インストールすると即時起動し、削除してもデータは保持します。手動コンソールを先に停止してください。

```bash
./scripts/console-service.sh install
./scripts/console-service.sh status
./scripts/console-service.sh logs
./scripts/console-service.sh restart
./scripts/console-service.sh stop
./scripts/console-service.sh start
./scripts/console-service.sh remove
```

ユーザーサービスの有効化だけでは無人起動を保証しません。Docker とユーザー管理プロセス（linger）は管理者が別途設定します。Ubuntu 26.04 x86_64 のラボで Python 3.12・Node 22・Docker のインストール、linger 設定後の実再起動と SSH ログイン前の自動起動、検査器2個・ポリシー・イベントの保持、合成通信の許可・遮断・マスキングを検証しました。他のホストや本番容量は別途検証が必要です。ユーザー管理プロセスの Docker グループ権限については英語ガイドを参照してください。サーバー間HAは未実装です。SQLiteをネットワークFSで共有しないでください。合成テストは本番認証ではありません。

[English reference](../en/operations.md) · [Inspector pool](inspector-pool.md)
