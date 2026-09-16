# Gateway Interface 0.37 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add standards-aligned JWT gateway authentication, independent target credentials, and verified HTTP/MCP client compatibility while preserving the 0.36 client-key path.

**Architecture:** The existing fixed-destination deployment gains separate `gateway_auth` and `target_auth` configuration models. Focused authentication and credential-provider modules feed the existing FastAPI adapter, which continues to sign and send the final request only through Envoy. OAuth issuance, stateful MCP, and streaming transport remain outside this release.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic 2, PyJWT/PyJWKClient, HTTPX, official MCP Python SDK 1.30.0, pytest, Envoy, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-09-17-gateway-interface-v037-design.md`

## Global Constraints

- English code, comments, configuration, and canonical documentation.
- Python indentation remains two spaces.
- One fixed upstream origin per deployment.
- Client credentials and target credentials are separate and never recorded in audit evidence.
- JWT validation is RS256-only and fails closed on issuer, audience, signature, time, scope, or JWKS errors.
- HTTP loopback exceptions require an explicit synthetic-only configuration flag.
- Client-key installations remain compatible with the 0.36 request path.
- MCP remains stateless bounded JSON over HTTP; long-lived SSE, WebSocket, cookies, and `Mcp-Session-Id` remain unsupported.
- No remote push, deployment, real tenant change, or customer environment change.

---

### Task 1: Authentication configuration contract

**Files:**
- Modify: `src/asr_proxy/selfhost/config.py`
- Modify: `tests/test_selfhost.py`
- Modify: `deploy/selfhost/deployment.yaml`

**Interfaces:**
- Produces: `ClientKeyGatewayAuth`, `JwtGatewayAuth`, `TargetAuth`, and normalized `Deployment.gateway_auth` / `Deployment.target_auth` values.
- Preserves: legacy `destination_auth` and `bearer_file` input normalization.

- [ ] **Step 1: Write failing configuration tests**

Add cases proving the default client-key/passthrough contract, structured static Bearer and API-key target credentials, legacy normalization, invalid reserved headers, non-HTTPS JWT endpoints, invalid resources, duplicate scopes, and the forbidden JWT-plus-passthrough combination.

```python
def test_jwt_gateway_requires_separate_target_credential(config):
  data=config.model_dump(exclude_none=True)
  data['gateway_auth']={
    'mode':'jwt', 'issuer':'https://issuer.example/tenant',
    'audience':'https://firewall.example/mcp',
    'jwks_uri':'https://issuer.example/jwks',
    'resource':'https://firewall.example/mcp',
    'authorization_servers':['https://issuer.example/tenant'],
    'required_scopes':['mcp.invoke'],
  }
  data['target_auth']={'mode':'passthrough_bearer'}
  with pytest.raises(ValueError,match='passthrough'):
    Deployment.model_validate(data)
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run: `.venv/bin/python -m pytest tests/test_selfhost.py -q`

Expected: failures because the structured models do not exist.

- [ ] **Step 3: Implement strict Pydantic models and legacy normalization**

Validate absolute issuer/JWKS/resource/authorization-server URLs, loopback-only HTTP exceptions, unique scopes, safe API-key header names, secret-file requirements, and authentication-mode combinations. Keep secrets out of `Deployment.public()`.

- [ ] **Step 4: Update the sample deployment and run focused tests**

Run: `.venv/bin/python -m pytest tests/test_selfhost.py -q`

Expected: configuration tests pass and the sample remains client-key plus target Bearer passthrough.

- [ ] **Step 5: Commit the configuration contract**

```bash
git add src/asr_proxy/selfhost/config.py tests/test_selfhost.py deploy/selfhost/deployment.yaml
git commit -m "Add separated gateway and target auth configuration"
```

### Task 2: Gateway JWT authenticator and target credential provider

**Files:**
- Create: `src/asr_proxy/selfhost/auth.py`
- Create: `src/asr_proxy/selfhost/credentials.py`
- Create: `tests/test_selfhost_auth.py`

**Interfaces:**
- Produces: `GatewayAuthResult`, `GatewayAuthenticator.authenticate(headers)`, `GatewayAuthenticator.metadata()`, `GatewayAuthenticator.challenge(error=None)`, and `TargetCredentialProvider.apply(headers, inbound_authorization)`.
- Consumes: normalized auth configuration from Task 1 and an injected JWT decoder or `PyJWKClient`.

- [ ] **Step 1: Write failing JWT and credential-provider tests**

Use an ephemeral RSA key to issue synthetic tokens. Test a valid token, wrong issuer, wrong audience, expired token, missing subject, missing scope, malformed authorization, JWKS failure, and key rotation. Prove that static target credentials replace removed inbound authorization and that configured API keys reject reserved headers.

```python
result=authenticator.authenticate({'authorization':'Bearer '+token})
assert result.subject=='synthetic-agent'
assert result.scopes==frozenset({'mcp.invoke'})

outgoing=provider.apply({'content-type':'application/json'}, result.authorization)
assert outgoing['authorization']=='Bearer synthetic-target-token'
assert token not in outgoing.values()
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run: `.venv/bin/python -m pytest tests/test_selfhost_auth.py -q`

Expected: import failure for the new modules.

- [ ] **Step 3: Implement authentication without exposing claims or token values**

Use `PyJWKClient` with bounded network timeout and cached keys. Decode with `algorithms=['RS256']`, configured issuer and audience, required `exp`, `iat`, and `sub`, and a small clock leeway. Convert all PyJWT/JWKS exceptions into stable internal reason codes.

- [ ] **Step 4: Implement target credential application**

Consume the inbound `Authorization` header before target injection. Support none, legacy Bearer passthrough, static Bearer, and static API-key modes. Detect conflicts before forwarding.

- [ ] **Step 5: Run the focused tests**

Run: `.venv/bin/python -m pytest tests/test_selfhost_auth.py -q`

Expected: all authenticator and provider tests pass.

- [ ] **Step 6: Commit authentication components**

```bash
git add src/asr_proxy/selfhost/auth.py src/asr_proxy/selfhost/credentials.py tests/test_selfhost_auth.py
git commit -m "Implement JWT gateway auth and target credentials"
```

### Task 3: Integrate authentication into the fixed gateway

**Files:**
- Modify: `src/asr_proxy/selfhost/gateway.py`
- Modify: `src/asr_proxy/selfhost/main.py`
- Modify: `tests/test_selfhost.py`

**Interfaces:**
- Consumes: Task 2 authenticator and target credential provider.
- Produces: public resource metadata, gateway-owned OAuth challenges, and independently authenticated forwarding through the existing signed Envoy path.

- [ ] **Step 1: Write failing adapter tests**

Add tests that metadata is public and not forwarded, JWT failures return `401` with `resource_metadata`, missing scopes return `403`, a valid JWT reaches Envoy without the inbound token, the target credential is injected, upstream challenges are suppressed, and client-key behavior remains unchanged.

```python
response=client.get('/.well-known/oauth-protected-resource')
assert response.json()['resource']=='https://firewall.example/mcp'

response=client.post('/mcp',headers={'authorization':'Bearer '+token},json=request)
assert response.status_code==200
assert seen.headers['authorization']=='Bearer synthetic-target-token'
assert token not in seen.headers.values()
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run: `.venv/bin/python -m pytest tests/test_selfhost.py -q`

Expected: failures for metadata, challenges, and separated credentials.

- [ ] **Step 3: Wire the modules into FastAPI and startup**

Build authenticators and providers once at startup. Authenticate before body reads and target calls. Serve only the configured metadata document locally. Generate gateway challenges only for gateway failures and continue suppressing target `WWW-Authenticate` headers.

- [ ] **Step 4: Run self-hosted unit tests**

Run: `.venv/bin/python -m pytest tests/test_selfhost.py tests/test_selfhost_auth.py -q`

Expected: all pass.

- [ ] **Step 5: Commit the gateway integration**

```bash
git add src/asr_proxy/selfhost/gateway.py src/asr_proxy/selfhost/main.py tests/test_selfhost.py
git commit -m "Separate inbound and target authentication in the gateway"
```

### Task 4: Verify official MCP SDK and generic HTTP compatibility

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/runtime/test_gateway_client_compat.py`
- Modify: `.github/workflows/test.yml`

**Interfaces:**
- Consumes: the sessionless gateway interface from Task 3.
- Produces: a pinned, repeatable official MCP SDK compatibility test and generic HTTP evidence.

- [ ] **Step 1: Add the pinned compatibility dependency and failing integration test**

Add a `compat` optional dependency containing `mcp==1.30.0`. Start the FastAPI gateway on an ephemeral loopback port, use HTTPX for generic calls, and use `mcp.client.streamable_http.streamable_http_client` with `ClientSession` for `initialize` and `list_tools`.

```python
async with streamable_http_client(url,http_client=http_client,terminate_on_close=False) as streams:
  async with ClientSession(streams[0],streams[1]) as session:
    initialized=await session.initialize()
    tools=await session.list_tools()
assert initialized.protocolVersion
assert [tool.name for tool in tools.tools]==['notes.read']
```

- [ ] **Step 2: Run the compatibility test and confirm protocol failures**

Run: `.venv/bin/python -m pytest tests/runtime/test_gateway_client_compat.py -q`

Expected: fail until the synthetic target returns MCP-valid initialize/discovery responses and the adapter preserves required response types.

- [ ] **Step 3: Complete the synthetic MCP target responses and test harness**

Return valid JSON-RPC responses for `initialize`, `tools/list`, and `notifications/initialized` without introducing a session ID. Assert every SDK request carries the configured client key and traverses the gateway transport.

- [ ] **Step 4: Add the test to proxy integration CI and run locally**

Run: `.venv/bin/python -m pytest tests/runtime/test_gateway_client_compat.py -q`

Expected: official MCP SDK and generic HTTP paths pass.

- [ ] **Step 5: Commit compatibility verification**

```bash
git add pyproject.toml tests/runtime/test_gateway_client_compat.py .github/workflows/test.yml
git commit -m "Verify gateway compatibility with the MCP SDK"
```

### Task 5: Update the Docker package contract

**Files:**
- Modify: `deploy/selfhost/compose.yaml`
- Modify: `tests/runtime/test_selfhost_runtime.py`

**Interfaces:**
- Consumes: normalized structured configuration and startup secret loading.
- Produces: a source-built 0.37 image verified with passthrough, static Bearer, static API-key, and HTTPS target cases.

- [ ] **Step 1: Convert Docker runtime tests to structured target authentication**

Add a static API-key case and assert the console exposes only the mode/header metadata, never the secret or token.

- [ ] **Step 2: Run the focused Docker test**

Run: `TD_SELFHOST_E2E=1 .venv/bin/python -m pytest tests/runtime/test_selfhost_runtime.py -q -s`

Expected: all configured lifecycle modes pass; an untrusted target CA still fails closed.

- [ ] **Step 3: Update the image tag and commit package changes**

```bash
git add deploy/selfhost/compose.yaml tests/runtime/test_selfhost_runtime.py
git commit -m "Package the 0.37 gateway authentication contract"
```

### Task 6: Document compatibility and release boundaries

**Files:**
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh-CN.md`
- Modify: `README.ja.md`
- Modify: `README.es.md`
- Modify: `README.fr.md`
- Create: `docs/en/gateway-compatibility.md`
- Create: `docs/ko/gateway-compatibility.md`
- Create: `docs/zh-CN/gateway-compatibility.md`
- Create: `docs/ja/gateway-compatibility.md`
- Create: `docs/es/gateway-compatibility.md`
- Create: `docs/fr/gateway-compatibility.md`
- Modify: `docs/*/self-hosting.md`
- Modify: `docs/*/deployment-fit.md`
- Modify: `docs/*/editions.md`
- Modify: `docs/*/console.md`
- Modify: `pyproject.toml`
- Modify: `CHANGELOG.md`
- Modify: `console/package.json`
- Modify: `console/package-lock.json`
- Modify: `console/src/DeploymentSettings.jsx`
- Modify: `console/src/locales/*.json`

**Interfaces:**
- Produces: English canonical instructions, six-language navigation and summaries, an evidence-labeled compatibility matrix, and version 0.37 metadata.

- [ ] **Step 1: Write the English compatibility guide**

Document exact VS Code and curl examples, client-key and JWT modes, target credentials, protected resource metadata, OAuth ownership, unsupported session/SSE behavior, and evidence labels for each tested path.

- [ ] **Step 2: Update the five translated guides and six README/version surfaces**

Keep commands and configuration keys identical across languages. Describe JWT tests as synthetic and do not claim real Entra, Conditional Access, HA, or customer deployment evidence.

- [ ] **Step 3: Run documentation consistency checks**

Run:

```bash
rg -n "0\.36|destination_auth" README*.md docs/*/{self-hosting,deployment-fit,editions,console,gateway-compatibility}.md deploy/selfhost pyproject.toml
```

Expected: only explicit legacy migration references use `destination_auth`; active release surfaces show 0.37.

- [ ] **Step 4: Run complete verification**

Run:

```bash
.venv/bin/python -m pytest -q
npm run check --prefix console
npm run build --prefix console
git diff --check
```

Expected: Python tests, console checks, console production build, and diff validation pass.

- [ ] **Step 5: Commit release documentation**

```bash
git add README*.md docs pyproject.toml CHANGELOG.md
git commit -m "Document the 0.37 gateway interface"
```

### Task 7: Final evidence review

**Files:**
- Review only: tracked changes and test outputs

**Interfaces:**
- Produces: a final local verification report that separates source tests, synthetic integration evidence, Docker evidence, and unverified live-provider behavior.

- [ ] **Step 1: Review the complete diff and repository status**

Run: `git status --short && git diff HEAD~6 --stat && git log -8 --oneline`

Expected: only 0.37 gateway, tests, version, and documentation changes are present.

- [ ] **Step 2: Confirm security invariants**

Verify from tests and source that JWTs are audience-bound, inbound tokens cannot reach a separately authenticated target, gateway credentials are removed before attestation, metadata is never proxied, target challenges do not leak, and every failure path avoids forwarding.

- [ ] **Step 3: Report local completion without pushing**

Report exact passing commands, skipped tests, commits, remaining real-provider and streaming limitations, and that no remote or landing system was changed.
