# Same-host operations — 0.34

[English](../en/operations.md) · [한국어](../ko/operations.md) · [简体中文](../zh-CN/operations.md) · [日本語](../ja/operations.md) · [Español](../es/operations.md) · [Français](../fr/operations.md)

## Console inspector processes

After installing the [console](console.md), open **Connections / System** to view worker PID, readiness and restart count. Administrators use **Settings → Inspector processes** to select **1, 2 or 4**, apply/start or stop inspection. Viewers have read-only access. Stopping inspectors intentionally blocks inline traffic; it does not remove the proxy or grant bypass access. Refresh reloads status.

All console workers use the same local policy/event database and replay database. New streams read the committed policy; an in-flight stream retains its request policy through response inspection. Replica changes restart the pool and the owned Envoy container. Expect an interruption. Failed changes attempt the prior configuration; failure to restore leaves inspection unavailable and traffic blocked. No tool request is automatically retried.

A child failure triggers bounded replacement with backoff (three replacements per child per supervisor lifetime). Exhausted recovery stops the entire pool. The console remains available to show the failure and let an administrator restart it. A stopped pool starts again when the whole console service restarts; stop is not a persistent maintenance policy. Health shows process/endpoint readiness, not proof that every detection succeeds.

The console uses gRPC ports **18101–18104** and health ports **18111–18114**, according to the selected count. Management remains `127.0.0.1:5176`, proxy defaults to `18082`, synthetic destination to `18090`. Only one console installation may own these fixed inspector/destination ports on a host.

Private `inspectors/` state contains logs, a status file and a runtime signing-key snapshot. Do not publish it. Status files can be stale after abrupt termination; the console checks the supervisor process and status timestamp. The signing key belongs to the synthetic console sender; this does not configure a production trusted adapter. Local event storage grows with traffic; plan retention and disk monitoring before long-running deployments.

The [standalone inspector pool](inspector-pool.md) uses an immutable YAML/key snapshot instead. It does **not** read console policies, and the console does not manage arbitrary external pools. Its key/policy changes require a complete pool restart.

## Opt-in Linux service

Requires a Linux user systemd session, the installed console assets/venv, and permission to use the existing local Docker daemon. Run as the installation user, without sudo:

```bash
./scripts/console-service.sh install
./scripts/console-service.sh status
./scripts/console-service.sh logs
./scripts/console-service.sh restart
./scripts/console-service.sh stop
./scripts/console-service.sh start
./scripts/console-service.sh remove
```

`install` creates and enables `~/.config/systemd/user/trapdefense-console.service` (or `$XDG_CONFIG_HOME/systemd/user`). It starts immediately. `remove` disables/stops the unit and removes only its unit file; persistent console data stays in place. Existing unit files are not overwritten. Do not install over a manually running console: stop your own console first. Inspect service logs after installation.

The unit uses a private umask, process-group shutdown and bounded service restart. It does not grant Docker access, enable user lingering, change host networking or provision Internet exposure. A user unit normally starts with the user manager/login. **Unattended boot requires a running Docker daemon and a persistent user manager (linger), configured by the host administrator.** No automatic boot claim is made by enabling this unit alone. For Entra environment variables, add an explicit `systemctl --user edit trapdefense-console.service` override as described in [identity](identity.md); never put credentials into the repository.

Validated on an Ubuntu 26.04 x86_64 lab host with Python 3.12, Node 22 and Docker: installation, an enabled user service with linger, automatic startup before SSH login after a real reboot, two restored inspectors, persisted policy/events and synthetic allow/block/redaction traffic. This is one lab configuration, not certification of other hosts or production capacity.

The lab also exposed stale Docker group membership in an already-running user manager: Docker worked in a new SSH shell but failed in the user service. Check `systemd-run --user --wait --pipe docker info` when diagnosing this difference. A planned reboot or an administrator-managed user-manager restart applies updated groups; do not broaden Docker socket permissions. Verify the service and an actual inspected request after installation.

## Verification and HA boundary

Tests cover real local Envoy forwarding, shared replay rejection after child replacement, committed policy visibility, Mirror evidence, PII redaction and all-inspectors-down blocking. These are synthetic same-host tests. They are not customer deployment, production sizing or real IdP evidence.

Server-to-server HA is **not included**. It needs atomic shared replay consumption, coordinated policy/key revisions, explicit network-partition behavior and failover tests preventing duplicate actions. Do not put the SQLite replay database on a network filesystem or create independent replay databases behind a load balancer and call that HA.
