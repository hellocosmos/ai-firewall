# 控制台安装与操作

[English](../en/console.md) · [한국어](../ko/console.md) · [简体中文](../zh-CN/console.md) · [日本語](../ja/console.md) · [Español](../es/console.md) · [Français](../fr/console.md)

## 安装与启动

需要 Python 3.11+、Node.js 22.12+ 或 24、npm，以及运行中的本地 Docker Engine/Desktop。仅需此仓库，无需 SDK、私有 Enterprise 包或模型 API。脚本优先使用已安装的 `uv`，否则使用 Python venv/pip。不要使用 sudo，并保持 Docker 在本地运行。

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall
./scripts/install-console.sh
./scripts/run-console.sh
```

打开 [http://127.0.0.1:5176](http://127.0.0.1:5176)，初始账户为 **admin / 1234** 。在 **设置 → 管理员密码** 中修改，修改后所有会话失效。控制台仅绑定回环地址，是本地评估安装，不是面向互联网的设备。端口冲突时停止启动，不会终止现有服务。按 Ctrl+C 停止，仅移除本安装拥有的 Envoy 容器。

## 语言

登录页和顶部栏提供语言选择。默认英语，另有韩语、简体中文、日语、西班牙语和法语。选择保存在浏览器中，不会退出登录；文档也以所选语言打开。工具名、规则代码、标识符和用户输入保持原样。界面翻译不会扩大相应语言的 PII 检测能力。

## 真实流量路径

```text
Browser -> management API/UI :5176
                 -> signed synthetic sender -> Envoy :18082 -> HTTP destination :18090
                                                 <-> gRPC inspector :18081
                 <- response inspection <- decision + receipt <- UI
```

发送器模拟 TLS 解密后的可信转发节点，对准确的合成请求签名，并不执行 TLS 解密或身份认证。Envoy 为真实代理，目标是独立 HTTP 监听器，不执行外部业务操作。Community 验证转发来源，而非用户或智能体身份。Access Broker 页面说明独立 Enterprise 的范围；Community 不提供模拟审批。

## 页面与首次使用

1. **仪表盘：** 运行笔记读取、客户信息脱敏、删除、提示注入、外部传输和响应 PII 场景。数据来自真实请求，而非预填决策。
2. **流量 / 事件：** 筛选并查看 HTTP 状态、目标接收、脱敏和策略版本。CSV 导出已清理的元数据。
3. **策略：** 将 `notes.read` 改为阻断，验证、应用并重新执行，完成后恢复允许。更新对新流生效，进行中的流保留原策略。
4. **连接 / 系统：** 查看组件就绪状态和实际路径。**审计：** 查看登录、策略及网络变更。
5. **设置：** 查看主机接口，修改代理监听端口、超时或正文上限。验证使用 Envoy 验证器；应用会短暂重启自有容器，检查新监听端口，失败时恢复旧配置。

## 网络设置与网卡

| 设置 | 默认值 / 含义 |
|---|---|
| 部署 | 显式 L7，单个回环接口 |
| 管理 API/UI | `127.0.0.1:5176` |
| 代理入口 | `127.0.0.1:18082`，可修改非特权端口 |
| 检查器 | `127.0.0.1:18081`，gRPC ExtProc |
| 目标 | `127.0.0.1:18090`，仅合成 HTTP |
| 请求超时 | 5 秒，可设为 2–30 秒 |
| 正文上限 | 1 MiB，可设为 1 KiB–1 MiB |
| 接口 | 实时主机名称、地址、链路状态、MTU 和安装角色 |

接口数量不是物理网卡数量，其中包括回环、桥接和隧道。当前配置仅使用回环，不设置物理单/双网卡路由、透明桥接、操作系统 IP/路由或物理出口绑定。此表单不开放任意生产目标。macOS 使用 Docker Desktop 主机转发，Linux 使用 host networking 访问回环。Envoy 1.39.1 固定到支持 amd64/arm64 的多架构 digest。

## 检查与故障模式

**Inline** 执行允许、阻断或脱敏；未映射、未签名的请求被拒绝，检查器通信失败时关闭转发。** 本控制台的 Mirror** 在同一同步代理路径上观察，不修改内容或消耗审批；通信故障仍会阻断。底层检查器的独立 mirror 收集器接收副本，不能影响原始流量。两者都不是无限实时流检查。代理失败时不会退回到直接调用引擎。

## 持久化与排障

`.runtime-state/console` 保存账户及会话哈希、策略、网络配置和清理后的 SQLite 事件。可用 `TD_CONSOLE_STATE` 指定其他私有目录。停止后备份；更改路径会创建独立安装。此目录被 Git 排除。演示签名密钥仅在进程中临时存在，不配置外部转发节点。目标接收计数在重启后清零，保存的交易证据保留。审计是可修改的本地存储，不是不可变存储。

启动失败时检查 Docker、5176/18081/18090 及配置的代理端口，不要自动终止无关服务。缺少检查证据表示错误，而非成功。延迟包含本地和容器影响，不代表生产基准。真实 TLS、IAM、强制路由、HA 和生产加固需要另行验证。

## 验证与翻译维护

```bash
.venv/bin/python -m pytest -q
npm run check --prefix console
npm run build --prefix console
# Stop the running console before this Docker test.
TD_CONSOLE_E2E=1 .venv/bin/python -m pytest tests/test_console.py -q
```

未设置 `TD_CONSOLE_E2E=1` 时跳过 Docker 测试。语言检查要求六个词典的键和占位符一致，并检查应用代码使用英语。修改英文键时同步更新全部 JSON，不改变稳定 API 代码。译文有差异时以英语为准。另见[架构](architecture.md)、[版本](editions.md)、[迁移](migration.md)和[安全](security.md)。
