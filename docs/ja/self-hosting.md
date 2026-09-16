# Docker セルフホスティング — 0.36 Community Preview

[English](../en/self-hosting.md) · [한국어](../ko/self-hosting.md) · [简体中文](../zh-CN/self-hosting.md) · [日本語](../ja/self-hosting.md) · [Español](../es/self-hosting.md) · [Français](../fr/self-hosting.md)

0.36 はアダプター、Envoy、検査器、管理 UI をまとめた Docker Compose プレビューです。イメージはソースからローカルでビルドします。TrapDefense Cloud は計画段階で、登録はできません。

クライアントで MCP/API URL を変更し、X-TD-Client-Key ヘッダーを追加できる必要があります。導入ごとに宛先を一つに固定し、ルートとツールを明示的にマッピングします。これらを設定できないクライアントはそのまま接続できません。

| 種別 | 対応範囲 |
|---|---|
| HTTP API | JSON、正確な method/path、最大 1 MiB、有限の応答 |
| MCP | ステートレス JSON POST、明示した制御メソッドとツール |
| 宛先認証 | 既存 Bearer/API Key の転送、またはサーバーファイルの固定 Bearer 注入 |
| 未対応 | OAuth ログイン仲介・トークン交換、Cookie/セッション、長時間 SSE、WebSocket、stdio、閉鎖型 SaaS 内部呼び出し |

管理者パスワードはコンソール用です。接続キーは TrapDefense へのアクセス用で、エージェントの本人確認ではありません。サービス権限は宛先が検証します。取得済み OAuth トークンの転送は OAuth ログイン仲介とは異なります。Entra コンソール SSO は既存のソースコンソール機能で、この Docker 構成には接続されていません。

## Docker

Git と Docker Compose v2 が必要です。init で 12 文字以上の管理者パスワードを設定します。既定のパスワードはありません。サンプルは合成宛先であり、実サービス連携の証明ではありません。

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall/deploy/selfhost
docker compose build app
docker compose run --rm app init
docker compose --profile smoke up -d
docker compose run --rm app client-key
```

http://localhost:18080 で admin としてログインします。client-key で接続キーを確認し、クライアントの秘密ヘッダー設定に保存します。ゲートウェイは http://localhost:18084、合成宛先のトークンは Bearer synthetic-target-token です。

実際の接続では deployment.yaml の upstream、authority、パス、ツール、resource を変更します。HTTPS 証明書を検証し、HTTP は信頼する区間でのみ明示的に許可します。passthrough は既存の認証ヘッダーを維持します。static_bearer は UID 10001 が読める 0600 の秘密ファイルをマウントし、入力 Authorization は拒否します。接続キーを共有する利用者は同じサービスアカウント権限を使います。

UI はポリシーとパスワードを管理します。マッピング変更時はバックアップ後に policy-reset、render、スタック再作成を行います。保存済みポリシーのみリセットし、アカウント・キー・イベントは保持します。新しい要求に新ポリシーが適用されます。

既定の公開アドレスはループバックです。遠隔利用には TLS プロキシと正確な console_origin が必要です。検査器と Envoy のホストポートは公開されません。経路迂回は顧客ネットワークで防止してください。

再起動しても名前付きボリュームの状態は保持されます。停止後に両ボリュームと設定をバックアップします。down -v はデータを削除します。ロールバックは旧イメージと対応するバックアップを復元します。リスナーの正常性だけでなく、許可・拒否要求と宛先の動作を確認してください。長時間ストリーム、HA、実顧客 IAM は別途検証が必要です。

[Detailed examples, backup and migration (English)](../en/self-hosting.md)
