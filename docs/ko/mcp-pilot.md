# 실제 MCP 파일럿 — 0.35 Open Source Preview

[English](../en/mcp-pilot.md) · [한국어](../ko/mcp-pilot.md) · [简体中文](../zh-CN/mcp-pilot.md) · [日本語](../ja/mcp-pilot.md) · [Español](../es/mcp-pilot.md) · [Français](../fr/mcp-pilot.md)

공식 MCP Python SDK 1.30.0의 실제 클라이언트·문서 서버를 기존 Envoy 검사 경로로 연결합니다. 프로토콜과 SQLite 문서 변경은 실제이며 데이터·공격 입력은 합성입니다. 고객 환경 인증이나 애플리케이션 SDK가 아닙니다.

저장소 루트에서 Python 3.11 이상과 실행 중인 Docker를 사용합니다. 매 실행마다 새로운 상태 디렉터리를 지정하세요. 기존 디렉터리는 덮어쓰지 않습니다.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,pilot]'
docker pull envoyproxy/envoy@sha256:57e14a549d7bd43c8d3f6d03e8cfa653e037d4b38e133acd9b54f38c524401b4
.venv/bin/python -m examples.mcp_pilot --state-dir .runtime-state/mcp-pilot-run --samples 30
```

클라이언트 → 로컬 인증·서명 어댑터 → Envoy·AI Firewall 검사기 → MCP 문서 서버 순서입니다. 에이전트에는 서명 키를 주지 않습니다. 어댑터 토큰은 로컬 접근용이며 사용자·에이전트 신원을 증명하지 않습니다. loopback과 같은 OS 사용자만으로 우회 방지가 보장되지는 않습니다. 운영 환경에서는 별도 라우팅·격리가 필요합니다.

초기화·도구 조회·읽기·수정, 삭제 차단과 원본 보존, 요청/응답 이메일 마스킹·가짜 Secret 차단, 알려진 악성 응답·미등록 도구·미서명 요청 차단, 검사기 장애 시 목적지 미실행을 확인합니다. 본문은 64 KiB로 제한합니다. 상태 없는 Streamable HTTP JSON 모드만 검증하며 장기 SSE·OAuth·임의 MCP 서버 호환성은 별도입니다.

**시그니처 밖의 의미 기반 악성 지시는 그대로 통과하는 사례가 있습니다. known_detection_miss로 기록하며 숨기지 않습니다. 모델이 거부하는 것과 방화벽 탐지는 다릅니다. 응답 차단은 도구 실행 후에 일어나므로 이미 발생한 부작용을 되돌리지 못합니다. 반복 정상 조회의 지연·오차단 결과는 전체 오탐률이나 기업 용량을 보장하지 않습니다.**

실제 로컬 LLM을 쓰려면 도구 호출을 지원하는 모델을 먼저 실행한 뒤 아래처럼 주소와 이름을 명시합니다. 실행기는 모델을 내려받거나 자동 선택하지 않으며 스크립트로 대체하지 않습니다. 원격 모델은 승인된 로컬 터널을 별도로 준비해야 합니다.

```bash
.venv/bin/python -m examples.mcp_pilot \
  --state-dir .runtime-state/mcp-agent-run --samples 30 \
  --model-url http://127.0.0.1:11434/v1 --model qwen3:1.7b
```

report.json은 도구 선택·실제 결과·차단 근거·모델 오류·미실행을 구분합니다. 원문이나 키는 포함하지 않습니다. 작업당 모델 6턴·도구 8회로 제한하며 동일 호출을 재실행하지 않습니다. 소유한 프로세스와 컨테이너는 종료하고 비공개 로그·DB·키는 상태 디렉터리에 남깁니다. 공유 전 보고서를 검토하세요. 자세한 신뢰 경계·인증 환경 변수·회귀 검증 명령은 [영문 가이드](../en/mcp-pilot.md)를 참고하세요.
