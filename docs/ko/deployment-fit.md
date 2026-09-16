# 배포 적합성과 제공 상태

[English](../en/deployment-fit.md) · [한국어](../ko/deployment-fit.md) · [简体中文](../zh-CN/deployment-fit.md) · [日本語](../ja/deployment-fit.md) · [Español](../es/deployment-fit.md) · [Français](../fr/deployment-fit.md)

지원하는 검사 경로로 전달할 수 있는 HTTP API·원격 MCP 호출을 보호합니다. MCP와 커넥터의 기존 서비스 인증을 활용하며 IAM을 대체하지 않습니다.

0.36은 어댑터·Envoy·검사기·운영 UI를 함께 실행하는 Docker Compose Preview입니다. 이미지는 소스에서 로컬 빌드합니다. TrapDefense Cloud는 계획 단계이며 가입할 수 없습니다.

클라이언트 접속 주소, 서버 진입점 또는 호환되는 네트워크 검사 경로를 제어할 수 있어야 합니다. 목적지 연결과 우회 방지가 필요합니다. SaaS 내부의 고정 호출, 로컬 stdio, Shell, 파일 및 직접 DB 작업은 HTTP 프록시 범위 밖입니다.

0.35 로컬 파일럿은 stateless Streamable HTTP의 JSON 응답을 검증합니다. 제한된 SSE 검사는 모든 스트리밍 MCP의 호환성 인증이 아닙니다. OAuth·상태 유지 세션·고객 신원 경로는 별도 검증이 필요합니다. Entra 콘솔 SSO는 Agent IAM이나 목적지 접근권한이 아닙니다.

[Architecture](architecture.md) · [Delivery status](editions.md) · [MCP pilot](mcp-pilot.md)

[Docker 셀프호스팅](self-hosting.md)
