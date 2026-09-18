# 배포 적합성과 제공 상태

> **AISG:** [연결 → 신원 → 통제 → 확인](aisg.md). Gateway 접속은 연결 키 또는 검증된 JWT로 인증합니다. 로컬 agent_key는 외부 IAM 없이 등록된 에이전트를 식별합니다. JWT identity_mode: agent는 검증된 테넌트·에이전트 정보를 사용하고, delegated는 사용자·작업·위임도 요구합니다. 기존 에이전트는 기본적으로 위임이 필요합니다.

[English](../en/deployment-fit.md) · [한국어](../ko/deployment-fit.md) · [简体中文](../zh-CN/deployment-fit.md) · [日本語](../ja/deployment-fit.md) · [Español](../es/deployment-fit.md) · [Français](../fr/deployment-fit.md)

지원하는 검사 경로로 전달할 수 있는 HTTP API·원격 MCP 호출을 보호합니다. MCP와 커넥터의 기존 서비스 인증을 활용하며 IAM을 대체하지 않습니다.

0.42은 연결 키 또는 외부 JWT 게이트웨이 인증과 별도 대상 자격증명을 포함한 Docker Compose Preview입니다. 이미지는 소스에서 빌드하며 TrapDefense Cloud는 계획 단계입니다.

클라이언트 접속 주소, 서버 진입점 또는 호환되는 네트워크 검사 경로를 제어할 수 있어야 합니다. 목적지 연결과 우회 방지가 필요합니다. SaaS 내부의 고정 호출, 로컬 stdio, Shell, 파일 및 직접 DB 작업은 HTTP 프록시 범위 밖입니다.

현재 검증은 실제 OpenAI→합성 MCP 흐름, 제공사 공식 SDK 합성 테스트, 실제 로컬 MCP·Keycloak과 VS Code 초기화·검색 증거를 포함합니다. 모델 SSE는 전체 버퍼링하며 상태 유지 MCP·고객 IAM 정책·서버 간 HA·운영 용량은 인증하지 않습니다. [0.42 검증과 한계](agent-workflow.md)를 확인하세요.

[Architecture](architecture.md) · [Delivery status](editions.md) · [MCP pilot](mcp-pilot.md)

[Docker 셀프호스팅](self-hosting.md) · [게이트웨이 호환성](gateway-compatibility.md)
