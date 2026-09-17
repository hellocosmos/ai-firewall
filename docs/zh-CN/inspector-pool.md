# AI Firewall 检查器进程池

[English](../en/inspector-pool.md) · [한국어](../ko/inspector-pool.md) · [简体中文](../zh-CN/inspector-pool.md) · [日本語](../ja/inspector-pool.md) · [Español](../es/inspector-pool.md) · [Français](../fr/inspector-pool.md)

在同一主机上运行 1、2 或 4 个检查器，并生成 Envoy 连接配置。该命令不会启动 Docker 或替换控制台。内置 Broker 支持同主机文件锁，但跨主机 HA 不在支持范围内。

所有进程共享同一个本地防重放数据库和审计日志。不要为每个进程创建独立数据库，也不要使用网络文件系统。相对路径以启动目录为基准。策略和密钥在启动时生成私有快照；变更需要重启整个池，并协调 Envoy 配置与签名端。

每个子进程默认最多重启 3 次，超出限制后整个池退出。失败请求不会自动重试；所有检查器停止时必须拒绝流量，不能绕过检查。

status.json 记录状态、PID、端口和重启次数。状态目录权限须为 0700，密钥仅限所有者访问。主管进程被强制终止后，子进程会退出，但状态文件和快照可能残留；请核对 PID、时间和实际健康状态。

默认 gRPC 从 18101 开始，健康端口从 18111 开始，代理端口为 18082。Docker Desktop 需要下面的附加参数，并仅发布主机回环端口；Linux 使用默认参数及 host network。控制台 UI 和系统服务管理集成尚未提供。

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
