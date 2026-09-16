# 게이트웨이 클라이언트 호환성 — 0.37

[English](../en/gateway-compatibility.md) · [한국어](../ko/gateway-compatibility.md) · [简体中文](../zh-CN/gateway-compatibility.md) · [日本語](../ja/gateway-compatibility.md) · [Español](../es/gateway-compatibility.md) · [Français](../fr/gateway-compatibility.md)

클라이언트는 원격 HTTP/MCP URL을 TrapDefense로 바꾸고 연결 키 헤더 또는 OAuth Bearer JWT를 사용할 수 있어야 합니다. 클라이언트→TrapDefense 인증과 TrapDefense→대상 인증은 분리됩니다.

| 경로 | 0.37 증거 |
|---|---|
| 일반 JSON HTTP | HTTPX 합성 통합 검증 완료 |
| 공식 Python MCP SDK 1.30.0 | 실제 SDK로 Streamable HTTP 초기화·알림·도구 목록 합성 통합 검증 완료 |
| VS Code 원격 MCP | 공식 `url`·`headers`·OAuth 설정과 호환되는 구성 예시 확인; VS Code 제품 실행은 미검증 |
| OAuth 메타데이터·RS256 JWT | 실제 HTTP JWKS 조회와 issuer/audience/time/subject/scope 합성 검증 완료 |
| 실제 Entra/Okta/Keycloak | 테넌트·TLS·Conditional Access·revocation 별도 검증 필요 |
| 세션 MCP·장기 SSE·WebSocket·stdio | 이 프로필에서 미지원 |

`gateway_auth`는 `client_key` 또는 `jwt`를 사용합니다. JWT 모드에서 TrapDefense는 OAuth Resource Server로 동작하며 RFC 9728 메타데이터와 `WWW-Authenticate` challenge를 제공합니다. 로그인, 토큰 발급, DCR, refresh와 OBO는 외부 IdP 또는 별도 credential provider가 담당합니다.

`target_auth`는 `none`, `passthrough_bearer`, `static_bearer`, `static_api_key`를 지원합니다. JWT 게이트웨이 토큰은 대상에 전달되지 않습니다. `passthrough_bearer`는 client-key 기반 레거시 HTTP 온보딩 전용이며 MCP OAuth 준수를 의미하지 않습니다.

실제 연동 승인 전 URL 변경, 양쪽 인증, MCP 초기화/도구 조회, 허용·차단, 대상 부작용, PII/secret, 대상 401, 검사 장애와 직접 URL fallback 여부를 함께 확인하세요. 상세 설정과 VS Code 예시는 [영문 가이드](../en/gateway-compatibility.md)를 참고하세요.
