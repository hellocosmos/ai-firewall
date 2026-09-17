# TrapDefense — 에이전트를 위한 AI 방화벽

[English](README.md) · [한국어](README.ko.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md)

> **Community Preview:** 로컬 평가와 연동 작업용입니다. 운영 트래픽·HA·용량·고객 신원 경로는 별도로 검증해야 합니다.

**프롬프트에서 실제 행동까지의 경로를 통제합니다.**

TrapDefense Community는 로컬 운영 UI를 갖춘 자체 호스팅 AI 방화벽입니다. 지원되는 HTTP·MCP 도구 호출을 검사하고, 실행 정책을 적용하며, 민감정보를 마스킹하고 판단 근거를 기록합니다. 기존 SDK는 [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security)에 유지됩니다.

```text
AI agents → TrapDefense AI Firewall → Tools / MCP servers / APIs
            Action policy · Data protection · Audit
          ← Inspected responses ←
```

제품의 논리적 흐름입니다. 신뢰 전달, 트래픽 가시성, 경로 강제 조건은 [배치 아키텍처](docs/ko/architecture.md)를 확인하세요.

Community는 단일 테넌트 Microsoft Entra ID 콘솔 SSO와 관리자·조회자 역할을 제공합니다. 콘솔 인증은 에이전트 실행 권한이 아니며 위임·승인은 Enterprise 기능입니다. [Entra SSO](docs/ko/identity.md).

## Docker 셀프호스팅 · 0.38

[Docker 셀프호스팅: integration contract, installation and verification](docs/ko/self-hosting.md)

0.38 Compatibility Lab은 공식 MCP SDK로 Entra·Okta·Keycloak 유사 claim, discovery, PKCE, RFC 8707 resource binding과 MCP `2025-11-25`를 검증합니다. 또한 digest를 고정한 공식 Keycloak 컨테이너의 실제 로컬 토큰과 VS Code 1.135의 실제 로컬 MCP 초기화·도구 조회를 검증합니다. 이는 재현 가능한 통합 증거이며 실제 고객 테넌트 인증은 아닙니다. [증거와 정확한 한계](docs/ko/gateway-compatibility.md).

## 배포 적합성과 제공 상태

지원하는 검사 경로로 전달할 수 있는 HTTP API·원격 MCP 호출을 보호합니다. MCP와 커넥터의 기존 서비스 인증을 활용하며 IAM을 대체하지 않습니다.

0.38은 어댑터·Envoy·검사기·운영 UI와 분리된 게이트웨이/대상 인증을 제공하는 Docker Compose Preview입니다. 연결 키 또는 외부 IdP의 JWT를 검증하고 별도 대상 자격증명을 사용합니다. 이미지는 소스에서 로컬 빌드하며 TrapDefense Cloud는 계획 단계입니다.

[제공 방식과 호환성](docs/ko/deployment-fit.md) · [게이트웨이 클라이언트 호환성](docs/ko/gateway-compatibility.md)

## TrapDefense가 다른 점

TrapDefense는 모델의 출력이 실제 행동으로 바뀌는 지점을 통제합니다. 프록시 기반 집행 경계, 로컬 데이터 보호, 명확한 신원 의미를 하나의 운영 경로로 결합합니다.

| 경계 | TrapDefense가 명확히 하는 것 |
|---|---|
| **독립 집행점** | 지원되는 HTTP·MCP 호출은 설정된 목적지에 도달하기 전에 Envoy와 검사기를 통과합니다. 애플리케이션에 기존 SDK를 넣을 필요가 없습니다. 배치 환경에서는 우회 방지 라우팅이 필요합니다. |
| **양방향 데이터 통제** | 지원되는 SSE를 포함한 완전하고 제한된 요청·응답에 행동·PII·Secret 정책을 적용해 허용·차단·마스킹할 수 있습니다. |
| **명확한 신원 경계** | Community Entra ID SSO는 콘솔 운영자를 인증합니다. 별도 Enterprise 파일럿은 사용자·에이전트·위임·작업·자원·행동을 함께 평가합니다. |
| **정직한 실패 의미** | Inline 검사 실패는 차단합니다. Mirror는 원본 트래픽과 승인 상태를 바꾸지 않고 `would_*` 가상 결과만 기록합니다. |
| **운영 가능한 증거** | 로컬 콘솔에서 판단, 정책 적용 범위, 목적지 수신증과 정제된 증거를 확인하며 보호 대상 원문은 감사 기록에 복사하지 않습니다. |

## 5분 로컬 평가

Python 3.11+, Node.js 22.12+ 또는 24, npm, 로컬 Docker Engine/Desktop이 필요합니다. 소스 설치이며 PyPI 배포를 의미하지 않습니다.

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall
./scripts/install-console.sh
./scripts/run-console.sh
```

[http://127.0.0.1:5176](http://127.0.0.1:5176)에서 `admin` / `1234`로 로그인한 후 설정에서 비밀번호를 변경하세요. 기본 언어는 영어입니다. 로그인 전후 언어 선택기를 사용할 수 있고 브라우저에 선택이 저장됩니다.

## 운영할 수 있는 기능

대시보드와 요청 증거, 로컬 허용·차단 정책, 전역·경로·도구별 PII 정책과 Mirror `would_*` 평가, 합성 HTTP 시나리오, 감사, 비밀번호 변경, 인터페이스 목록, 리스너·업스트림 설정, 소유한 Envoy 컨테이너의 검증·적용·롤백을 제공합니다.

합성 요청은 실제 Envoy → gRPC 검사기 → HTTP 목적지를 통과합니다. 목적지 수신 증거와 응답 마스킹을 기록하며 엔진 직접 호출로 대체하지 않습니다. 기본 리스너는 `127.0.0.1:18082`, 검사기는 `18101–18104`, 합성 목적지는 `18090`입니다.

## 범위와 에디션

Community에는 로컬 정책, 명시적 HTTP/MCP 매핑, 신뢰 홉 서명, 제한된 응답/SSE 검사와 정제된 로컬 증거가 포함됩니다. Enterprise Access Broker는 별도 배포하는 비공개 파일럿이며 Community 콘솔 SSO가 에이전트 신원, 위임 접근, 승인을 제공하는 것은 아닙니다.

NIC 목록과 토폴로지 설명을 제공합니다. loopback 데모는 OS 주소, 2-NIC 라우팅, 투명 브리지, 물리 출구를 설정하지 않습니다. inline 검사 실패는 차단합니다. 콘솔 Mirror는 동기 경로를 관찰하며 별도 mirror 수집기는 원본을 차단할 수 없습니다.

## 로컬 성능 기준선

콘솔을 중지한 뒤 같은 Envoy → gRPC 검사기 → 합성 HTTP 경로를 순차 측정합니다.

```bash
.venv/bin/trapdefense-benchmark --scenario read --iterations 30
```

JSON 결과의 p50/p95 지연과 결과 개수는 로컬 회귀 비교용이며 운영 처리량이나 용량을 입증하지 않습니다. [벤치마크 안내](docs/ko/benchmark.md)를 참고하세요.

## 문서와 검증

[콘솔 안내](docs/ko/console.md) · [Architecture](docs/ko/architecture.md) · [Community / Enterprise](docs/ko/editions.md) · [벤치마크](docs/ko/benchmark.md) · [SDK → Proxy](docs/ko/migration.md) · [Security](docs/ko/security.md)

애플리케이션 코드는 영어로 작성하고 UI 사전 6개를 함께 유지합니다. 오프라인 PII 검사는 영어·한국어·중국어 간체·일본어·스페인어·프랑스어의 명시적 패턴과 검증기를 지원합니다. 이름·위치·주소를 포괄하는 범용 NER은 제공하지 않습니다. 각 번역 문서 상단에서 언어를 전환할 수 있습니다.

결정적 Secret 검사는 지원 본문·응답·SSE에서 알려진 provider 토큰, 서명 JWT, Azure Storage SAS 링크, 민감 필드의 고엔트로피 자격증명을 차단합니다. 요청 자격증명 헤더는 서명 검증된 매핑 목적지에만 전달하고 감사 증거에서는 제외합니다. 정확한 범위와 한계는 [Security](docs/ko/security.md)를 확인하세요.

```bash
.venv/bin/python -m pytest -q
npm run check --prefix console
npm run build --prefix console
# Stop the running console before this Docker test.
TD_CONSOLE_E2E=1 .venv/bin/python -m pytest tests/test_console.py -q
```

합성 로컬 검증이며 고객 TLS/IdP 연동, 운영 경로 강제, HA, 성능 인증이 아닙니다. 탐지에는 오탐·미탐이 있으며 로컬 감사는 불변 저장소가 아닙니다.

## License

Community는 MIT 라이선스입니다. 비공개 Enterprise 코드와 고객 자산은 포함하지 않습니다.


## 동일 서버 운영 — 0.34

Connections / System에서 PID·상태·재시작 횟수를 확인합니다. 관리자는 Settings → Inspector processes에서 1·2·4개를 선택하고 적용/시작/중지할 수 있습니다. Viewer는 조회만 가능합니다. 중지 중에는 인라인 트래픽이 차단됩니다.

[Operations](docs/ko/operations.md) · [Inspector pool](docs/ko/inspector-pool.md)

## 실제 MCP 파일럿 (0.35 Community Preview)

실제 MCP 초기화·도구 조회·문서 작업을 방화벽 경로로 실행하고 로컬 LLM 에이전트를 선택적으로 연결합니다. 합성 데이터·탐지 한계·직접/프록시 지연을 구분합니다.

[MCP pilot](docs/ko/mcp-pilot.md)
