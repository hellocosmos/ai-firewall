# Community 与 Enterprise

[English](../en/editions.md) · [한국어](../ko/editions.md) · [简体中文](../zh-CN/editions.md) · [日本語](../ja/editions.md) · [Español](../es/editions.md) · [Français](../fr/editions.md)

Community 是本仓库采用 MIT 许可的代理运行时和本地控制台，包含受信转发跳签名验证、显式 HTTP/MCP 映射、本地策略、特征检测、PII 脱敏、有界响应/SSE 检查、净化审计记录、本地登录、密码修改和代理设置。无需私有软件包或外部模型 API。

Enterprise 通过单独分发的 Access Broker 增加用户、代理、任务委派，访问决策以及一次性、有期限、绑定请求的人工审批。现有 IAM 上下文必须来自可信集成，仍须验证真实客户 IdP。Community 界面会标明未包含的功能。

私有提供程序通过 Python `trapdefense.authorizers` / `enterprise` 入口连接。`authorize(request)` 执行授权，`evaluate(request)` 提供不修改状态的 mirror 评估。选择 Enterprise 而缺少提供程序时启动失败。Broker 令牌记录是限定范围的决策证据，不是通用 OAuth 访问令牌。

集中设备管理、分布式高可用、托管计费及不可变审计存储尚未交付。商业范围可包含私有提供程序、部署、策略集成和支持，价格及支持条款另行约定。本地 SQLite 和 JSONL 仍可修改。
