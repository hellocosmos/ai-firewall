# Community와 Enterprise

[English](../en/editions.md) · [한국어](../ko/editions.md) · [简体中文](../zh-CN/editions.md) · [日本語](../ja/editions.md) · [Español](../es/editions.md) · [Français](../fr/editions.md)

Community는 단일 테넌트 Microsoft Entra ID 콘솔 SSO와 관리자·조회자 역할을 제공합니다. 콘솔 인증은 에이전트 실행 권한이 아니며 위임·승인은 Enterprise 기능입니다. [Entra SSO](identity.md).

## 현재 제공 상태

| 경계 | 상태 | 증거와 제한 |
|---|---|---|
| Community 런타임·콘솔 | **공개 Community Preview** | 이 MIT 저장소에 공개되어 있고 CI와 합성 Envoy 경로 검증을 통과합니다. 운영 트래픽과 용량은 고객 환경에서 별도 검증해야 합니다. |
| Enterprise Access Broker | **비공개 파일럿 구현** | 별도 제공자와 승인 흐름이 구현되어 있지만 이 저장소에 없고 일반 출시로 표현하지 않습니다. 실제 IAM·고객 정책·장애 경로 검증이 필요합니다. |
| 중앙 Fleet·분산 HA·불변 감사·Hosted Service | **로드맵** | 출시되지 않았으며 Community 화면이 이를 구현한 것으로 표현하지 않습니다. |

에디션 명칭은 제품·라이선스 경계를 나타내며 모든 Enterprise 로드맵 항목이 일반 출시됐다는 의미가 아닙니다.

Community는 이 저장소의 MIT 라이선스 프록시 런타임과 로컬 운영 UI입니다. 서명된 전달 홉 검증, 명시적 HTTP/MCP 매핑, 로컬 정책, 패턴 검사, PII 마스킹, 크기가 제한된 응답/SSE 검사, 정제된 감사 기록, 로컬 로그인·비밀번호 변경·프록시 설정을 제공합니다. 비공개 패키지나 외부 모델 API가 필요하지 않습니다.

별도 배포하는 Enterprise 파일럿 구현은 Access Broker를 추가합니다. 사용자·에이전트·작업 위임, 접근 판단, 만료되는 일회용 요청 단위 승인을 제공합니다. 기존 IAM 정보는 신뢰할 수 있는 연동으로 전달해야 하며 실제 고객 IdP 검증이 필요합니다. Community UI에는 미포함 기능이 표시됩니다.

비공개 제공자는 Python `trapdefense.authorizers` / `enterprise` 진입점으로 연결합니다. `authorize(request)`는 접근을 집행하고, `evaluate(request)`는 상태를 변경하지 않는 mirror 평가를 수행합니다. 제공자 없이 Enterprise를 선택하면 시작이 실패합니다. Broker 토큰 기록은 범위가 정해진 판단 증거이며 범용 OAuth 접근 토큰이 아닙니다.

중앙 장비 관리, 분산 HA, 호스팅 과금, 변경 불가능한 감사 저장소는 출시 기능이 아닙니다. 상용 범위에는 비공개 제공자, 구축, 정책 연동과 지원이 포함될 수 있으며 가격·지원 조건은 별도입니다. 로컬 SQLite와 JSONL은 수정 가능한 저장소입니다.
