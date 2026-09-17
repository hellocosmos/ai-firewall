# AI Firewall インスペクタープール

[English](../en/inspector-pool.md) · [한국어](../ko/inspector-pool.md) · [简体中文](../zh-CN/inspector-pool.md) · [日本語](../ja/inspector-pool.md) · [Español](../es/inspector-pool.md) · [Français](../fr/inspector-pool.md)

同一ホストで検査プロセスを 1・2・4 個起動し、Envoy 接続設定を生成します。Docker の起動やコンソールの置き換えは行いません。内蔵 Broker は同一ホストの file lock をサポートしますが、ホスト間 HA は対象外です。

全プロセスで同じローカル再送防止 DB と監査ログを共有します。プロセス別 DB やネットワークファイルシステムは使用しないでください。相対パスは起動ディレクトリ基準です。ポリシーと鍵は起動時の非公開スナップショットに固定され、変更にはプール全体の再起動と Envoy・署名側の調整が必要です。

子プロセスの再起動は既定で最大 3 回です。上限に達するとプール全体を停止します。失敗した要求は自動再送せず、全検査器停止時も検査を迂回しません。

status.json に状態、PID、ポート、再起動回数を記録します。状態ディレクトリは 0700、鍵は所有者のみアクセス可能にしてください。管理プロセスの強制終了後は子も終了しますが、状態ファイルやスナップショットが残るため、PID・時刻・実際の状態を確認してください。

既定の gRPC は 18101 から、ヘルス確認は 18111 から、プロキシは 18082 です。Docker Desktop は以下の追加引数とホストのループバック公開を使用します。Linux は既定設定と host network を使用します。コンソール UI とサービス管理の連携は未提供です。

```bash
.venv/bin/trapdefense-inspector-pool \
  --config "$PWD/.runtime-state/pool-demo/inspector.yaml" \
  --key-file "$PWD/.runtime-state/pool-demo/attestation.key" \
  --state-directory "$PWD/.runtime-state/pool-supervisor" \
  --envoy-output "$PWD/.runtime-state/pool-envoy.yaml" \
  --replicas 2
```

```text
--proxy-bind 0.0.0.0 --inspector-address host.docker.internal --upstream-address host.docker.internal
```

[Complete setup and limits / English](../en/inspector-pool.md)
