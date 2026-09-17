# Contributing to TrapDefense AI Firewall

Thank you for helping improve the public AI Firewall. TrapDefense 0.39 is one MIT-licensed codebase: the Runtime Gateway, HTTP/MCP inspector, data controls, built-in Agent Access Broker, human approval, sanitized evidence, console and Docker self-hosting all live in this repository.

## Before opening a change

- Search existing issues and keep the change focused on one problem.
- For bugs, include the exact revision, environment, trigger, expected behavior and actual behavior.
- Use synthetic inputs. Never attach customer traffic, secrets, credentials, tokens or raw sensitive content.
- Report suspected vulnerabilities through [SECURITY.md](SECURITY.md), not a public issue.

## Local setup

Requires Python 3.11+, Node.js 22.12+ (or 24), npm and Docker Engine/Desktop.

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall
./scripts/install-console.sh
```

Run the checks that match your change:

```bash
.venv/bin/python -m pytest -q
npm run check --prefix console
npm run build --prefix console

# Stop the running console before this Docker integration test.
TD_CONSOLE_E2E=1 .venv/bin/python -m pytest tests/test_console.py -q
```

The Docker test exercises the local Envoy to gRPC inspector to synthetic HTTP destination path. It does not certify production routing, a customer TLS path, a real identity provider, high availability or performance.

## Change guidelines

- Keep public code, identifiers, comments and documentation in English.
- Preserve the separation between console authentication and agent action authorization.
- Keep fail-closed behavior for inline inspection failures.
- Keep approval decisions bound to the exact request digest and consume them once.
- Add or update a focused test when behavior or a security boundary changes.
- Update the English documentation and every affected locale when user-visible text changes.
- Avoid new dependencies unless the change cannot be implemented safely with the current stack.

## Pull requests

Explain the concrete trigger and the resulting behavior. Include:

1. What changed and why.
2. The security or operational impact.
3. Commands run and their results.
4. Tests or environments skipped, with the reason.
5. Known limitations.

Passing checks do not prove a production deployment. Maintainers may request a smaller design, stronger synthetic evidence or a customer-specific integration outside the generic product contract.
