# TrapDefense — エージェント向け AI ファイアウォール

[English](README.md) · [한국어](README.ko.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md)

**AI の行動を制御し、データを保護します。**

TrapDefense Community はローカル運用 UI を備えたセルフホスト型 AI ファイアウォールです。対応する HTTP・MCP ツール呼び出しを検査し、実行ポリシーを適用して機密データをマスキングし、判断の証跡を記録します。旧 SDK は [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security) に残ります。

```text
AI agents → TrapDefense AI Firewall → Tools / MCP servers / APIs
            Action policy · Data protection · Audit
          ← Inspected responses ←
```

製品の論理的な流れです。信頼済み転送、通信の可視性、経路の要件は[配置アーキテクチャ](docs/ja/architecture.md)を参照してください。

Community は単一テナントの Microsoft Entra ID コンソール SSO と管理者・閲覧者ロールを提供します。コンソール認証はエージェントの実行認可ではなく、委任と承認は Enterprise の機能です。 [Entra SSO](docs/ja/identity.md).

## コンソールのインストールと起動

Python 3.11+、Node.js 22.12+ または 24、npm、ローカル Docker Engine/Desktop が必要です。ソースからのインストールであり、PyPI 公開を意味しません。

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall
./scripts/install-console.sh
./scripts/run-console.sh
```

[http://127.0.0.1:5176](http://127.0.0.1:5176) を開き、`admin` / `1234` でログインして設定からパスワードを変更してください。既定は英語です。ログイン前後で言語を選択でき、ブラウザーに保存されます。

## 運用機能

ダッシュボード、要求の証拠、ローカル許可・遮断・PII ポリシー、合成 HTTP シナリオ、監査、パスワード変更、インターフェイス一覧、リスナー・上流設定、所有 Envoy コンテナーの検証・適用・ロールバック。

合成要求は実際の Envoy → gRPC 検査器 → HTTP 宛先を通ります。宛先の受信記録と応答マスキングを記録し、エンジン直接呼び出しで代用しません。既定リスナーは `127.0.0.1:18082`、検査器は `18081`、合成宛先は `18090` です。

## 範囲とエディション

Community はローカルポリシー、明示的 HTTP/MCP マッピング、信頼ホップ署名、上限付き応答/SSE 検査、機密情報を除いた証拠を含みます。Enterprise Access Broker は別配布です。Community のコンソール SSO はエージェントの本人確認、委任アクセス、承認を提供しません。

NIC 一覧と構成説明を含みます。ループバックのデモは OS アドレス、2 NIC ルーティング、透過ブリッジ、物理出口を設定しません。inline 検査失敗は遮断します。コンソール Mirror は同期経路を観察し、別の mirror コレクターは原本を遮断できません。

## ドキュメントと検証

[コンソールガイド](docs/ja/console.md) · [Architecture](docs/ja/architecture.md) · [Community / Enterprise](docs/ja/editions.md) · [SDK → Proxy](docs/ja/migration.md) · [Security](docs/ja/security.md)

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
