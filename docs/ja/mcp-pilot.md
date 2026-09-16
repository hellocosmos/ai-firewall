# 実 MCP パイロット — 0.35 Community Preview

[English](../en/mcp-pilot.md) · [한국어](../ko/mcp-pilot.md) · [简体中文](../zh-CN/mcp-pilot.md) · [日本語](../ja/mcp-pilot.md) · [Español](../es/mcp-pilot.md) · [Français](../fr/mcp-pilot.md)

公式 MCP Python SDK 1.30.0 のクライアントと文書サーバーを既存の Envoy 検査経路に接続します。プロトコルと SQLite 文書変更は実動作、データと攻撃入力は合成です。顧客環境の認証やアプリケーション SDK ではありません。

リポジトリ直下で Python 3.11 以上と稼働中の Docker を使用します。毎回新しい状態ディレクトリを指定します。既存ディレクトリは上書きしません。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,pilot]'
docker pull envoyproxy/envoy@sha256:57e14a549d7bd43c8d3f6d03e8cfa653e037d4b38e133acd9b54f38c524401b4
.venv/bin/python -m examples.mcp_pilot --state-dir .runtime-state/mcp-pilot-run --samples 30
```

クライアント → ローカル認証・署名アダプター → Envoy/Community 検査器 → MCP 文書サーバー。エージェントは署名鍵を持ちません。アダプタートークンはローカルアクセス用で、ユーザーやエージェントの身元証明ではありません。同一 OS ユーザーとループバックだけでは本番の分離になりません。迂回を防ぐ経路設定が必要です。

初期化、ツール一覧、読み書き、削除拒否と原本保持、要求/応答のメールアドレス秘匿、ダミー Secret 拒否、既知の悪意ある応答、未登録ツール、未署名要求、検査器停止時の下流未実行を確認します。本文は64 KiB。ステートレス Streamable HTTP JSON のみを検証し、長時間 SSE・OAuth・任意サーバー互換性は別途検証します。

**シグネチャ外の意味的な悪意ある指示がそのまま通過するケースを known_detection_miss として記録します。モデルの拒否はファイアウォール検知ではありません。応答遮断はツール実行後で、副作用を取り消せません。反復した正常読み取りの遅延や誤遮断は一般的な誤検知率・企業規模の容量を保証しません。**

実 LLM 検証にはツール呼び出し対応ローカルモデルを先に起動し、URL とモデル名を明示します。実行器はモデルのダウンロード・自動選択・スクリプト代替を行いません。リモートモデルには別途承認済みのローカルトンネルを用意してください。

```bash
.venv/bin/python -m examples.mcp_pilot \
  --state-dir .runtime-state/mcp-agent-run --samples 30 \
  --model-url http://127.0.0.1:11434/v1 --model qwen3:1.7b
```

report.json はツール選択、実結果、遮断理由、モデルエラー、未実行を区別し、原文や鍵を含めません。タスクごとに最大6ターン・8ツール呼び出しで同一呼び出しを繰り返しません。所有するプロセスとコンテナは終了し、非公開ログ・DB・鍵は状態ディレクトリに残ります。共有前に報告を確認してください。詳細と認証環境変数・回帰コマンドは[英語ガイド](../en/mcp-pilot.md)を参照してください。
