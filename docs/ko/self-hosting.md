# Docker 셀프호스팅 — 0.36 Community Preview

[English](../en/self-hosting.md) · [한국어](../ko/self-hosting.md) · [简体中文](../zh-CN/self-hosting.md) · [日本語](../ja/self-hosting.md) · [Español](../es/self-hosting.md) · [Français](../fr/self-hosting.md)

0.36은 어댑터·Envoy·검사기·운영 UI를 함께 실행하는 Docker Compose Preview입니다. 이미지는 소스에서 로컬 빌드합니다. TrapDefense Cloud는 계획 단계이며 가입할 수 없습니다.

클라이언트에서 MCP/API URL을 변경하고 `X-TD-Client-Key` 헤더를 추가할 수 있어야 합니다. 설치별 목적지는 하나이며 경로·도구를 명시적으로 매핑합니다. 이 설정이 불가능하면 바로 연동할 수 없습니다.

| 구분 | 지원 범위 |
|---|---|
| HTTP API | JSON, 정확한 method/path, 최대 1 MiB, 유한 응답 |
| MCP | 무상태 JSON POST, 명시적으로 등록된 제어 메서드·도구 |
| 대상 인증 | 기존 Bearer/API Key 전달 또는 서버 파일의 고정 Bearer 주입 |
| 미지원 | OAuth 로그인 중개·토큰 교환, 쿠키/세션, 장시간 SSE, WebSocket, stdio, 폐쇄형 SaaS 내부 호출 |

**인증 세 가지를 구분하세요.** 관리자 비밀번호는 콘솔 로그인용입니다. 연결 키는 TrapDefense 접근용이며 에이전트 신원 증명이 아닙니다. 대상 서비스 토큰은 해당 서비스가 권한을 확인합니다. OAuth로 미리 발급받은 토큰 전달은 OAuth 로그인 중개와 다릅니다. Entra 콘솔 SSO는 기존 소스 콘솔 기능이며 이 Docker 구성에는 연결되어 있지 않습니다.

## Docker

Git과 Docker Compose v2가 필요합니다. `init`에서 12자 이상 관리자 비밀번호를 지정합니다. 기본 비밀번호는 없습니다. 예제 설정은 합성 목적지를 사용하므로 실제 서비스 연동으로 오해하지 마세요.

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall/deploy/selfhost
docker compose build app
docker compose run --rm app init
docker compose --profile smoke up -d
docker compose run --rm app client-key
```

`http://localhost:18080`에 admin으로 로그인합니다. `client-key`로 연결 키를 확인해 클라이언트의 비밀 헤더 설정에 보관하세요. 게이트웨이는 `http://localhost:18084`입니다. 합성 목적지 토큰은 `Bearer synthetic-target-token`입니다.

실제 연결 시 `deployment.yaml`의 upstream·authority·경로·도구·resource를 바꾸세요. HTTPS 인증서를 검증하며 HTTP는 신뢰 구간에서만 명시적으로 허용합니다. `passthrough`는 서비스 인증 헤더를 유지합니다. `static_bearer`는 UID 10001이 읽을 수 있는 0600 비밀 파일을 마운트하며 입력 Authorization과 충돌하면 거부합니다. 공유 연결 키 사용자는 같은 서비스 계정 권한을 사용합니다.

UI는 정책·비밀번호를 관리합니다. 매핑 변경은 백업 후 `policy-reset`으로 기존 정책을 명시적으로 초기화하고 `render`와 재생성을 수행하세요. 계정·키·이벤트는 보존됩니다. 새 요청부터 정책이 적용됩니다.

기본 공개 주소는 루프백입니다. 원격 사용은 TLS 프록시와 정확한 `console_origin` 설정이 필요합니다. 검사기와 Envoy는 호스트에 포트를 공개하지 않습니다. 경로 우회 차단은 고객 네트워크에서 구성해야 합니다.

재시작 후 named volume의 정책·키·감사 기록은 유지됩니다. 중지 후 두 볼륨과 설정을 함께 백업하세요. `down -v`는 데이터를 삭제합니다. 롤백은 이전 이미지와 일치하는 백업을 함께 복원합니다. 리스너 정상만으로 연동 성공을 판단하지 말고 허용·차단 요청과 대상 효과를 확인하세요. 장시간 스트림·HA·실제 고객 IAM은 별도 검증 대상입니다.

[Detailed examples, backup and migration (English)](../en/self-hosting.md)
