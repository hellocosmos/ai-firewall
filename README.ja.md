# TrapDefense — エージェント向け AI ファイアウォール

[English](README.md) · [한국어](README.ko.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md)

> **Community Preview:** ローカル評価と統合作業向けです。本番通信、HA、容量、顧客の ID 経路は別途検証が必要です。

**プロンプトから実際のアクションまでの経路を制御します。**

TrapDefense Community はローカル運用 UI を備えたセルフホスト型 AI ファイアウォールです。対応する HTTP・MCP ツール呼び出しを検査し、実行ポリシーを適用して機密データをマスキングし、判断の証跡を記録します。旧 SDK は [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security) に残ります。

```text
AI agents → TrapDefense AI Firewall → Tools / MCP servers / APIs
            Action policy · Data protection · Audit
          ← Inspected responses ←
```

製品の論理的な流れです。信頼済み転送、通信の可視性、経路の要件は[配置アーキテクチャ](docs/ja/architecture.md)を参照してください。

Community は単一テナントの Microsoft Entra ID コンソール SSO と管理者・閲覧者ロールを提供します。コンソール認証はエージェントの実行認可ではなく、委任と承認は Enterprise の機能です。 [Entra SSO](docs/ja/identity.md).

## 導入条件と提供状況

対応する検査経路を通る HTTP API・リモート MCP 呼び出しを保護します。MCP サーバーとコネクターの既存認証を維持し、IAM を置き換えません。

Self-hosted Community は Docker プロキシの例を含むソースベースのプレビューです。統合 Docker インストールパッケージは計画段階です。同じ検査基盤を使うマネージド TrapDefense Cloud も計画段階で、登録・利用はまだできません。

[提供形態と互換性](docs/ja/deployment-fit.md)

## TrapDefense の違い

TrapDefense はモデル出力が実際のアクションに変わる地点を制御します。プロキシ型の実行境界、ローカルのデータ保護、明確な ID の意味を一つの運用経路にまとめます。

| 境界 | TrapDefense が明確にすること |
|---|---|
| **独立した実行点** | 対応する HTTP・MCP 呼び出しは、設定済みの宛先へ到達する前に Envoy と検査器を通過します。アプリへの旧 SDK 組み込みは不要です。配備時には迂回を防ぐルーティングが必要です。 |
| **双方向のデータ制御** | 対応する SSE を含む完全かつ上限付きの要求・応答に、アクション、PII、Secret ポリシーを適用し、許可・遮断・マスキングできます。 |
| **明確な ID 境界** | Community の Entra ID SSO はコンソール運用者を認証します。別配布の Enterprise パイロットは、ユーザー・エージェント・委任・タスク・リソース・アクションをまとめて評価します。 |
| **明確な障害時動作** | Inline の検査失敗は遮断します。Mirror は元の通信や承認状態を変更せず、`would_*` の仮想結果だけを記録します。 |
| **運用可能な証跡** | ローカルコンソールで判断、ポリシー範囲、宛先の受信証跡、サニタイズ済み証拠を確認でき、保護対象の本文を監査へコピーしません。 |

## 5 分間のローカル評価

Python 3.11+、Node.js 22.12+ または 24、npm、ローカル Docker Engine/Desktop が必要です。ソースからのインストールであり、PyPI 公開を意味しません。

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall
./scripts/install-console.sh
./scripts/run-console.sh
```

[http://127.0.0.1:5176](http://127.0.0.1:5176) を開き、`admin` / `1234` でログインして設定からパスワードを変更してください。既定は英語です。ログイン前後で言語を選択でき、ブラウザーに保存されます。

成功の基準は、**接続 / システム**でプロキシ、検査器、宛先が準備完了になり、**業務ノートを読む**の実行結果に HTTP 200 と宛先受信の証跡が表示されることです。初期パスワードはループバックデモ専用なので、直ちに変更してください。この手順はインターネット公開サービス、本番ルーティング、実際の業務宛先を構成しません。

## 運用機能

ダッシュボード、要求の証拠、ローカル許可・遮断ポリシー、グローバル・ルート・ツール別 PII ポリシーと Mirror `would_*` 評価、合成 HTTP シナリオ、監査、パスワード変更、インターフェイス一覧、リスナー・上流設定、所有 Envoy コンテナーの検証・適用・ロールバック。

合成要求は実際の Envoy → gRPC 検査器 → HTTP 宛先を通ります。宛先の受信記録と応答マスキングを記録し、エンジン直接呼び出しで代用しません。既定リスナーは `127.0.0.1:18082`、検査器は `18101–18104`、合成宛先は `18090` です。

## 範囲とエディション

Community はローカルポリシー、明示的 HTTP/MCP マッピング、信頼ホップ署名、上限付き応答/SSE 検査、機密情報を除いた証拠を含みます。Enterprise Access Broker は別配布の非公開パイロットです。Community のコンソール SSO はエージェントの本人確認、委任アクセス、承認を提供しません。

NIC 一覧と構成説明を含みます。ループバックのデモは OS アドレス、2 NIC ルーティング、透過ブリッジ、物理出口を設定しません。inline 検査失敗は遮断します。コンソール Mirror は同期経路を観察し、別の mirror コレクターは原本を遮断できません。

## ローカル性能ベースライン

コンソールを停止し、同じ Envoy → gRPC 検査器 → 合成 HTTP 経路を順次測定します。

```bash
.venv/bin/trapdefense-benchmark --scenario read --iterations 30
```

JSON の p50/p95 遅延と結果件数はローカル回帰比較用であり、本番のスループットや容量を証明しません。[ベンチマーク](docs/ja/benchmark.md)を参照してください。

## ドキュメントと検証

[コンソールガイド](docs/ja/console.md) · [Architecture](docs/ja/architecture.md) · [Community / Enterprise](docs/ja/editions.md) · [ベンチマーク](docs/ja/benchmark.md) · [SDK → Proxy](docs/ja/migration.md) · [Security](docs/ja/security.md)

アプリケーションコードは英語で、完全な UI 辞書を 6 言語で管理します。オフライン PII 検査は英語、韓国語、簡体字中国語、日本語、スペイン語、フランス語の明示的なパターンと検証器に対応します。氏名、場所、住所を網羅する汎用 NER は提供しません。各ガイド上部で言語を切り替えられます。

決定的 Secret 検査は、対応する本文・レスポンス・SSE 内の認識可能なプロバイダートークン、署名付き JWT、Azure Storage SAS リンク、機密フィールドの高エントロピー資格情報を遮断します。リクエストの資格情報ヘッダーは署名検証済みのマッピング先だけに渡し、監査証拠から除外します。範囲と制限は [Security](docs/ja/security.md) を参照してください。

```bash
.venv/bin/python -m pytest -q
npm run check --prefix console
npm run build --prefix console
# Stop the running console before this Docker test.
TD_CONSOLE_E2E=1 .venv/bin/python -m pytest tests/test_console.py -q
```

これはローカル合成検証であり、顧客 TLS/IdP 連携、本番経路強制、HA、性能の認証ではありません。検査には誤検知・見逃しがあり、ローカル監査は不変保存ではありません。

## License

Community は MIT ライセンスです。非公開 Enterprise コードと顧客資産は含みません。


## 同一ホストの運用 — 0.34

Connections / System で PID、状態、再起動回数を確認します。管理者は Settings → Inspector processes で 1・2・4 プロセスを選び、適用・開始・停止できます。Viewer は閲覧のみです。停止中はインライン通信を遮断します。

[Operations](docs/ja/operations.md) · [Inspector pool](docs/ja/inspector-pool.md)

## 実 MCP パイロット（0.35 Community Preview）

実際の MCP 初期化・一覧・文書ツールを検査経路で実行し、ローカル LLM を任意接続します。合成データ・検知限界・直接/プロキシ遅延を区別します。

[MCP pilot](docs/ja/mcp-pilot.md)
