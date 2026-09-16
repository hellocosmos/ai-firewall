# 旧 SDK からの移行

[English](../en/migration.md) · [한국어](../ko/migration.md) · [简体中文](../zh-CN/migration.md) · [日本語](../ja/migration.md) · [Español](../es/migration.md) · [Français](../fr/migration.md)

旧組み込み Python SDK と履歴は [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security) に残ります。このリポジトリは新しい Community プロキシ製品です。SDK 互換性や自動パッケージ移行は提供しません。

1. 保護する HTTP/MCP 呼び出しと宛先を整理します。
2. TLS 復号後に信頼できる署名アダプターを配置し、プロキシ経由を強制します。
3. ツール・操作マッピング、上限、マスキング対象フィールドを明示します。
4. 合成データで観察した後、inline の許可・マスキング・遮断・障害動作を検証します。
5. 委任アクセスやリクエスト単位承認が必要な場合、非公開 Enterprise プロバイダーを追加します。

既存 SDK は固定バージョンを維持し、別経路でパイロットを評価できます。[コンソールガイド](console.md)から始めてください。ソースからのインストールは PyPI 公開や顧客環境の更新を意味しません。更新前に状態をバックアップし、合成環境の資格情報や署名鍵を本番へコピーしないでください。
