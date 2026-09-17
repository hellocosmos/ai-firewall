# Unified Open Source Product Implementation Plan

> **For Codex:** Execute this plan in order, preserve unrelated workspace changes, and stop only after validation, remote push, and landing deployment evidence are complete.

**Goal:** Release TrapDefense 0.39 as one MIT-licensed repository with the built-in Access Broker and no private runtime dependency.

**Architecture:** Preserve the Runtime Gateway and Access Broker as distinct boundaries. Move the broker implementation into `asr_proxy.access_broker`, select it with `access_broker_enabled`, map verified JWT claims to signed normalized identity in self-hosted mode, and operate it through the existing console.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, PyJWT, Envoy ext_proc, React/Vite, Docker Compose, pytest.

---

### Task 1: Publish the built-in Access Broker core

**Files:**
- Create: `src/asr_proxy/access_broker/{__init__,models,store,broker}.py`
- Modify: `src/asr_proxy/inspection/{authorization,contracts,engine,server,pool}.py`
- Create/modify: broker and inspection tests under `tests/`

**Steps:**
1. Port the existing strict broker models, transactional file store, approval binding, and audit behavior into the public package.
2. Add focused tests for registration, delegation, strict digest binding, tenant isolation, approval replay rejection, and multi-process file-store safety.
3. Replace edition and entry-point branches with optional built-in broker construction.
4. Run focused broker and inspection tests.

### Task 2: Connect verified self-hosted identity

**Files:**
- Modify: `src/asr_proxy/selfhost/{config,auth,gateway,runtime}.py`
- Modify: `deploy/selfhost/*`
- Modify: self-hosted tests under `tests/`

**Steps:**
1. Add explicit JWT-to-agent identity claim mapping.
2. Return only normalized identity from verified JWTs; do not propagate arbitrary claims.
3. Sign normalized identity into the trusted-hop attestation and configure the built-in broker store.
4. Reject incomplete broker/JWT combinations at startup.
5. Test allow, block, approval, wrong-tenant, and missing-claim behavior end to end.

### Task 3: Operate the broker from the console

**Files:**
- Modify: `src/asr_proxy/console/{runtime,app,scenarios}.py`
- Modify: `console/src/{Console,Broker,Policies}.jsx` and locale files
- Modify: `tests/test_console.py` and console tests

**Steps:**
1. Seed the local synthetic demo into the real file-backed broker.
2. Expose agent, delegation, approval, approval-decision, and demo-renewal endpoints.
3. Route the deployment scenario through real request-bound approval.
4. Remove edition upsell behavior and label the broker Experimental.
5. Run API tests, locale-key parity, and the production console build.

### Task 4: Rename and document release 0.39

**Files:**
- Modify: `pyproject.toml`, Docker/Compose files, README and release docs
- Modify: `docs/{en,ko,zh,ja,es,fr}/**`
- Modify: documentation tests

**Steps:**
1. Rename the package/image to `trapdefense-ai-firewall` and set version 0.39.
2. Replace Community/Enterprise product split with one open-source product and optional broker mode.
3. Document claim mapping, security boundaries, migration, and evidence limitations in six languages.
4. Run documentation link/locale checks and scan for stale edition/private-provider claims.

### Task 5: Validate and publish the repository

**Files:**
- Modify only validation fixes required by evidence.

**Steps:**
1. Run full pytest, console build, Docker Compose configuration/smoke, protocol harnesses, and secret/private-path scans.
2. Review the complete diff for public-boundary leaks and security regressions.
3. Commit coherent changes, push `main`, and verify the GitHub Actions workflow.

### Task 6: Reposition and deploy trapdefense.com

**Files:**
- Modify: `trapdefense-pilot-kit/landing/index.html`
- Modify: `trapdefense-pilot-kit/landing/docs/**/*.html`
- Modify: `trapdefense-pilot-kit/landing/enterprise/index.html`
- Modify: shared landing assets only as needed

**Steps:**
1. Present one open-source product, self-hosting, built-in Experimental Access Broker, and planned managed cloud/support.
2. Remove edition-gated language and keep implementation/evidence labels accurate.
3. Validate links, contact flow, responsive layout, and screenshots locally.
4. Commit only landing files in the parent repository, push `main`, deploy static files with backup, verify public hashes/pages/contact service, and visually inspect production.
