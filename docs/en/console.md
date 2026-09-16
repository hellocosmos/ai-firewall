# Console installation and operation

[English](../en/console.md) · [한국어](../ko/console.md) · [简体中文](../zh-CN/console.md) · [日本語](../ja/console.md) · [Español](../es/console.md) · [Français](../fr/console.md)

Community includes single-tenant Microsoft Entra ID console SSO with Administrator and Viewer roles. Console authentication does not authorize agent actions; delegation and approval remain Enterprise features. [Entra SSO](identity.md).

## Install and start

Requirements: Python 3.11+, Node.js 22.12+ (or 24), npm, and a running local Docker Engine/Desktop. Install from this repository; no SDK, private Enterprise package or model API is required. Scripts use an existing `uv` installation when available, otherwise Python venv/pip. Run without sudo and keep Docker local.

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall
./scripts/install-console.sh
./scripts/run-console.sh
```

Open [http://127.0.0.1:5176](http://127.0.0.1:5176). The first account is **admin / 1234** . Change it in **Settings → Administrator password** ; changing it revokes all sessions. The console binds to loopback and is a local evaluation installation, not an Internet-facing appliance. A port conflict stops startup without killing existing services. Stop with Ctrl+C; only this installation's labeled Envoy container is removed.

## Language

Use the language selector on the sign-in page or top bar. English is the default; Korean, Simplified Chinese, Japanese, Spanish and French are included. Selection persists in this browser and does not sign you out. Documentation opens in the selected language. Tool names, rule codes, identifiers and user-entered content remain unchanged. UI translation does not expand PII-language coverage.

## Actual traffic path

```text
Browser -> management API/UI :5176
                 -> signed synthetic sender -> Envoy :18082 -> HTTP destination :18090
                                                 <-> gRPC inspector :18081
                 <- response inspection <- decision + receipt <- UI
```

The sender simulates a trusted forwarding hop after TLS decryption. It signs exact synthetic requests; it is not a TLS decryptor or identity provider. Envoy is real, and the no-op destination is a separate HTTP listener. No external business action occurs. Community verifies the forwarding source, not user/agent identity. The Access Broker page explains the separate Enterprise boundary; Community provides no fake approvals.

## Pages and a first walkthrough

1. **Dashboard:** run Read business notes, Redact customer data, Delete protected notes, injection, external transfer and response PII scenarios. Data is produced by real requests, not prefilled verdicts.
2. **Traffic / Events:** filter decisions and open details. Check HTTP status, destination receipt, masking and policy version. CSV exports contain sanitized metadata.
3. **Policies:** change `notes.read` to block, validate, apply, and rerun. Restore allow when finished. Updates apply to new streams; in-flight streams retain their policy snapshot.
4. **Connections / System:** inspect component readiness and the actual path. ** Audit:** review sign-in, policy and network changes.
5. **Settings:** inspect host interfaces and change the proxy listener port, timeout or body limit. Validate invokes Envoy's validator. Apply briefly restarts the owned container, checks the new listener and restores the previous configuration on failure.

## Network settings and NICs

| Setting | Default / meaning |
|---|---|
| Deployment | Explicit L7, single loopback interface |
| Management API/UI | `127.0.0.1:5176` |
| Proxy ingress | `127.0.0.1:18082`, configurable unprivileged port |
| Inspector | `127.0.0.1:18081`, gRPC ExtProc |
| Destination | `127.0.0.1:18090`, synthetic HTTP only |
| Request timeout | 5 seconds; configurable 2–30 |
| Body limit | 1 MiB; configurable 1 KiB–1 MiB |
| Interfaces | Live host names, addresses, link state, MTU and installation role |

Interface count is not physical NIC count: loopback, bridges and tunnels are included. The installed profile uses loopback; it does not configure physical one-/two-NIC routing, transparent bridging, OS IP/routes or physical egress pinning. Arbitrary production destinations are not exposed by this form. On macOS, Docker Desktop forwards to host services. Linux uses host networking for loopback reachability. Envoy 1.39.1 is pinned by a multi-architecture digest (amd64/arm64).

## Inspection and failure modes

**Inline** allows, blocks or masks. Unmapped/unsigned requests are denied. An inspector communication failure fails closed. ** Mirror in this console** observes the same synchronous proxy path without modifying content or consuming approvals; communication failures still block. The separate mirror collector in the lower-level inspector receives copies and cannot affect the original. Neither is unbounded streaming inspection. No direct-engine fallback is used when the proxy fails.

## Persistence and troubleshooting

`.runtime-state/console` stores account hashes, session hashes, policy, network settings and sanitized SQLite events. Set `TD_CONSOLE_STATE` to a different private directory if needed. Back it up while stopped; changing the path starts a separate installation. It is excluded from Git. The signing key is ephemeral within this demo; external trusted hops are not provisioned. Destination receipt counters reset on process restart; saved transaction evidence remains. Audit is local and editable, not immutable.

If startup fails, check Docker availability and ports 5176/18081/18090 plus the configured proxy port. Do not stop unrelated services automatically. Missing inspection evidence is an error, not success. Runtime latency includes local/container effects and is not a production benchmark. Real TLS equipment, IAM, forced routing, HA and production hardening require separate validation.

## Verify and maintain translations

```bash
.venv/bin/python -m pytest -q
npm run check --prefix console
npm run build --prefix console
# Stop the running console before this Docker test.
TD_CONSOLE_E2E=1 .venv/bin/python -m pytest tests/test_console.py -q
```

Without `TD_CONSOLE_E2E=1`, Docker tests are skipped. Locale checks require identical keys and placeholders across all six dictionaries and English application source. Update English keys and all locale JSON files together; keep stable API codes unchanged. English documentation is the reference when translations differ. See [architecture](architecture.md), [editions](editions.md), [migration](migration.md) and [security](security.md).
