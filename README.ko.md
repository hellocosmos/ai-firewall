# TrapDefense — AI Firewall for Agents

[English](README.md) · [아키텍처](docs/architecture.md) · [Community / Enterprise](docs/editions.md)

**기존 TLS decryptor 뒤에서 AI agent의 HTTP/MCP 요청과 응답을 검사하는 프록시 보안 제품입니다.**

```text
AI Agent → TLS 복호화 → 신뢰된 forwarding adapter
                         → Envoy + TrapDefense 검사기 → 지정된 목적지
                           ← 응답 검사 ←
```

## Community

- 명시적으로 매핑한 HTTP 경로와 MCP tool/action에 허용·차단 정책 적용
- PII 마스킹, egress 검사, 알려진 prompt injection 패턴 탐지
- 요청·응답 및 지원되는 SSE 형식의 제한된 버퍼 검사
- 원본 요청에 결합된 신뢰 구간 서명, 유효기간 및 재생 공격 검사
- 민감 원문을 제외한 로컬 JSONL 감사 기록
- SDK·Enterprise 패키지·외부 모델 API 없이 실행, MIT 라이선스

[영문 README의 실행 명령](README.md#run-the-local-demo)으로 합성 요청의 허용·마스킹·차단을 확인할 수 있습니다. 기본 데모는 Python 3.11+와 Docker Desktop을 사용합니다.

Community는 신뢰한 전달 지점을 검증하며 사용자·에이전트 신원을 보증하지 않습니다. Enterprise는 별도 비공개 Access Broker로 사용자·에이전트·위임·작업 기반 판단과 요청별 승인을 확장합니다. Enterprise 설정에서 해당 플러그인이 없으면 시작에 실패합니다.

TLS 복호화만으로 연결이 완료되지는 않습니다. 신뢰된 어댑터의 요청 서명, 정확한 HTTP 전달, 우회 방지와 네트워크 격리가 필요합니다. 실제 고객 복호화 장비·IdP·HA는 별도 검증 대상입니다. Mirror는 관찰 전용이며 원본 요청을 차단하지 않습니다. SSE는 크기·시간 제한 안에서 버퍼링합니다. 탐지 패턴은 모든 prompt injection 방어를 보장하지 않습니다.

이 저장소는 새 프록시 제품입니다. 이전 SDK는 [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security)에 보존하며 새 Community 배포에는 포함하지 않습니다.
