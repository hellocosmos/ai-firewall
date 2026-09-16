# 同一主机运维 — 0.34

[English](../en/operations.md) · [한국어](../ko/operations.md) · [简体中文](../zh-CN/operations.md) · [日本語](../ja/operations.md) · [Español](../es/operations.md) · [Français](../fr/operations.md)

在 Connections / System 查看 PID、状态和重启次数。管理员可在 Settings → Inspector processes 选择 1、2 或 4 个进程并应用、启动或停止。Viewer 仅可查看。停止期间阻止内联流量。

控制台工作进程共享本地策略、事件和防重放数据库。新请求读取已提交策略，进行中的请求保持原策略直到响应检查结束。调整进程数会短暂重启进程池和 Envoy；失败时尝试恢复，恢复失败则继续阻止流量。不自动重试工具请求。

每个子进程最多替换三次，超限停止整个进程池。重启控制台服务会重新启动进程池。独立 CLI 进程池不读取控制台策略；更改 YAML 或密钥后必须整体重启。

需要 Linux 用户 systemd 会话和现有 Docker 权限。以安装用户运行，不使用 sudo。安装立即启动，移除保留数据。请先停止手动运行的控制台。

```bash
./scripts/console-service.sh install
./scripts/console-service.sh status
./scripts/console-service.sh logs
./scripts/console-service.sh restart
./scripts/console-service.sh stop
./scripts/console-service.sh start
./scripts/console-service.sh remove
```

启用用户服务并不保证无人值守启动。管理员须另行配置 Docker 和持久用户管理器（linger）。已在 Ubuntu 26.04 x86_64 实验主机上验证 Python 3.12、Node 22、Docker 安装，配置 linger 后真实重启、SSH 登录前自动启动、两个检查器和策略/事件保留，以及合成允许、阻止和脱敏流量。其他主机和生产容量仍需验证。用户管理器的 Docker 组权限问题请参阅英文指南。未实现跨服务器 HA。不要在网络文件系统上共享 SQLite。合成测试不是生产认证。

[English reference](../en/operations.md) · [Inspector pool](inspector-pool.md)
