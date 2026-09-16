# Community と Enterprise

[English](../en/editions.md) · [한국어](../ko/editions.md) · [简体中文](../zh-CN/editions.md) · [日本語](../ja/editions.md) · [Español](../es/editions.md) · [Français](../fr/editions.md)

## 導入条件と提供状況

Self-hosted Community は Docker プロキシの例を含むソースベースのプレビューです。統合 Docker インストールパッケージは計画段階です。同じ検査基盤を使うマネージド TrapDefense Cloud も計画段階で、登録・利用はまだできません。

[提供形態と互換性](deployment-fit.md)

Community は単一テナントの Microsoft Entra ID コンソール SSO と管理者・閲覧者ロールを提供します。コンソール認証はエージェントの実行認可ではなく、委任と承認は Enterprise の機能です。 [Entra SSO](identity.md).

## 現在の提供状況

| 境界 | 状況 | 証跡と制限 |
|---|---|---|
| Community ランタイムとコンソール | **公開 Community Preview** | この MIT リポジトリで公開され、CI と合成 Envoy 経路の検証に合格しています。本番通信と容量は顧客環境で別途検証が必要です。 |
| Enterprise Access Broker | **非公開パイロット実装** | 別配布のプロバイダーと承認フローは存在しますが、このリポジトリには含まれず、一般提供とは表現しません。実 IAM、顧客ポリシー、障害経路の検証が必要です。 |
| 集中 Fleet、分散 HA、不変監査、ホステッドサービス | **ロードマップ** | 未提供であり、Community 画面が実装済みであることを示すものではありません。 |

エディション名は製品とライセンスの境界を示し、すべての Enterprise ロードマップ項目が一般提供済みであることを意味しません。

Community は、このリポジトリの MIT ライセンスのプロキシランタイムとローカル運用コンソールです。信頼された転送ホップの署名検証、明示的な HTTP/MCP マッピング、ローカルポリシー、パターン検査、PII マスキング、上限付き応答/SSE 検査、機密情報を除いた監査記録、ローカルログイン、パスワード変更、プロキシ設定を提供します。非公開パッケージや外部モデル API は不要です。

別配布の Enterprise パイロット実装は Access Broker により、ユーザー・エージェント・タスクの委任、アクセス判定、有効期限付きで一度だけ使えるリクエスト単位の承認を追加します。既存 IAM の情報は信頼できる連携から取得し、実際の顧客 IdP で検証する必要があります。Community UI は含まれない機能を明示します。

非公開プロバイダーは Python の `trapdefense.authorizers` / `enterprise` エントリーポイントに接続します。`authorize(request)` は判定を適用し、`evaluate(request)` は状態を変更しない mirror 評価を行います。プロバイダーなしで Enterprise を選ぶと起動に失敗します。Broker のトークン記録は範囲付きの判定証拠であり、汎用 OAuth アクセストークンではありません。

集中管理、分散 HA、ホスティング課金、不変監査ストレージは未提供です。商用範囲には非公開プロバイダー、導入、ポリシー連携、サポートを含められます。価格と支援条件は別途定めます。ローカル SQLite と JSONL は変更可能です。
