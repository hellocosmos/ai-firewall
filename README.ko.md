# TrapDefense — 에이전트를 위한 AI 방화벽

[English](README.md) · [한국어](README.ko.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md)

**AI의 행동을 통제하고 데이터를 보호합니다.**

TrapDefense Community는 로컬 운영 UI를 갖춘 자체 호스팅 AI 방화벽입니다. 지원되는 HTTP·MCP 도구 호출을 검사하고, 실행 정책을 적용하며, 민감정보를 마스킹하고 판단 근거를 기록합니다. 기존 SDK는 [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security)에 유지됩니다.

```text
AI agents → TrapDefense AI Firewall → Tools / MCP servers / APIs
            Action policy · Data protection · Audit
          ← Inspected responses ←
```

제품의 논리적 흐름입니다. 신뢰 전달, 트래픽 가시성, 경로 강제 조건은 [배치 아키텍처](docs/ko/architecture.md)를 확인하세요.

Community는 단일 테넌트 Microsoft Entra ID 콘솔 SSO와 관리자·조회자 역할을 제공합니다. 콘솔 인증은 에이전트 실행 권한이 아니며 위임·승인은 Enterprise 기능입니다. [Entra SSO](docs/ko/identity.md).

## 콘솔 설치와 실행

Python 3.11+, Node.js 22.12+ 또는 24, npm, 로컬 Docker Engine/Desktop이 필요합니다. 소스 설치이며 PyPI 배포를 의미하지 않습니다.

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall
./scripts/install-console.sh
./scripts/run-console.sh
```

[http://127.0.0.1:5176](http://127.0.0.1:5176)에서 `admin` / `1234`로 로그인한 후 설정에서 비밀번호를 변경하세요. 기본 언어는 영어입니다. 로그인 전후 언어 선택기를 사용할 수 있고 브라우저에 선택이 저장됩니다.

## 운영할 수 있는 기능

대시보드와 요청 증거, 로컬 허용·차단·PII 정책, 합성 HTTP 시나리오, 감사, 비밀번호 변경, 인터페이스 목록, 리스너·업스트림 설정, 소유한 Envoy 컨테이너의 검증·적용·롤백을 제공합니다.

합성 요청은 실제 Envoy → gRPC 검사기 → HTTP 목적지를 통과합니다. 목적지 수신 증거와 응답 마스킹을 기록하며 엔진 직접 호출로 대체하지 않습니다. 기본 리스너는 `127.0.0.1:18082`, 검사기는 `18081`, 합성 목적지는 `18090`입니다.

## 범위와 에디션

Community에는 로컬 정책, 명시적 HTTP/MCP 매핑, 신뢰 홉 서명, 제한된 응답/SSE 검사와 정제된 로컬 증거가 포함됩니다. Enterprise Access Broker 구현은 별도 배포하며 Community 콘솔 SSO가 에이전트 신원, 위임 접근, 승인을 제공하는 것은 아닙니다.

NIC 목록과 토폴로지 설명을 제공합니다. loopback 데모는 OS 주소, 2-NIC 라우팅, 투명 브리지, 물리 출구를 설정하지 않습니다. inline 검사 실패는 차단합니다. 콘솔 Mirror는 동기 경로를 관찰하며 별도 mirror 수집기는 원본을 차단할 수 없습니다.

## 문서와 검증

[콘솔 안내](docs/ko/console.md) · [Architecture](docs/ko/architecture.md) · [Community / Enterprise](docs/ko/editions.md) · [SDK → Proxy](docs/ko/migration.md) · [Security](docs/ko/security.md)

애플리케이션 코드는 영어로 작성하고 UI 사전 6개를 함께 유지합니다. 오프라인 PII 검사는 영어·한국어·중국어 간체·일본어·스페인어·프랑스어의 명시적 패턴과 검증기를 지원합니다. 이름·위치·주소를 포괄하는 범용 NER은 제공하지 않습니다. 각 번역 문서 상단에서 언어를 전환할 수 있습니다.

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
