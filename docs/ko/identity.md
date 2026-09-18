# Microsoft Entra ID — TrapDefense console SSO

**설치 경로:** Docker 배포는 [설치 가이드](self-hosting.md)를 따릅니다. 별도 소스 콘솔의 Entra SSO·합성 데모 설정은 Docker에 자동 적용되지 않습니다.

> **AISG:** [연결 → 신원 → 통제 → 확인](aisg.md). Gateway 접속은 연결 키 또는 검증된 JWT로 인증합니다. 로컬 agent_key는 외부 IAM 없이 등록된 에이전트를 식별합니다. JWT identity_mode: agent는 검증된 테넌트·에이전트 정보를 사용하고, delegated는 사용자·작업·위임도 요구합니다. 기존 에이전트는 기본적으로 위임이 필요합니다.

[English](../en/identity.md) · [한국어](../ko/identity.md) · [简体中文](../zh-CN/identity.md) · [日本語](../ja/identity.md) · [Español](../es/identity.md) · [Français](../fr/identity.md)

콘솔은 관리자·조회자 역할의 단일 테넌트 Microsoft Entra ID SSO를 지원합니다. 콘솔 운영자 인증과 에이전트 인가는 별도 경계이며, 에이전트 인가는 내장 Access Broker가 담당합니다.

## Configuration

단일 테넌트 Web 앱을 등록하고 아래 콜백을 정확히 등록하세요. 사용자 앱 역할 `TrapDefense.Admin`, `TrapDefense.Viewer`를 만들고 Enterprise applications에서 할당 필요를 활성화한 뒤 테스트 사용자를 배정합니다. 설정은 저장소 밖에 0600 권한으로 보관합니다. 비밀값은 서버에만 두며 Graph 권한은 필요하지 않습니다.

```json
{
  "tenant_id": "YOUR-TENANT-UUID",
  "client_id": "YOUR-APPLICATION-UUID",
  "client_secret": "YOUR-SERVER-SIDE-SECRET",
  "redirect_uri": "http://localhost:5176/demo-api/auth/callback"
}
```

```bash
chmod 600 /absolute/path/entra.json
TD_ENTRA_CONFIG=/absolute/path/entra.json ./scripts/run-console.sh
```

## Synthetic demo

```bash
TD_SYNTHETIC_ENTRA=1 ./scripts/run-console.sh
```

`http://127.0.0.1:5176` → **Sign in with Synthetic Entra** → **Admin / Viewer**.

조회자는 대시보드·이벤트·정책·네트워크·감사만 읽으며 로그아웃 외 쓰기는 서버에서 차단합니다. Entra 비밀번호는 Entra에서 관리합니다. 세션은 최대 1시간이며 ID 토큰 만료를 넘지 않습니다. 역할 변경은 다음 로그인에 적용되고 기존 세션을 지속 재검증하지 않습니다. 로그아웃은 로컬 세션만 종료합니다. 실제 Entra 설정 시 로컬 로그인은 기본 비활성입니다. 복구 계정은 기본 비밀번호 변경 후 `TD_CONSOLE_LOCAL_LOGIN=1`로 명시적으로 활성화합니다. 콘솔은 loopback 전용입니다. 합성 성공은 실제 테넌트·동의·MFA·Conditional Access 검증이 아닙니다.

## Protocol

Authorization code + PKCE S256, browser-bound one-time state, nonce, RS256 signature, issuer, audience, tenant and app-role validation. Tokens and client secrets are never sent to browser storage or audit logs. Synthetic mode uses an ephemeral RSA issuer with local code redemption; no Microsoft token endpoint is called. Real mode uses Microsoft authorization/token/JWKS endpoints and does not register synthetic routes.

[Microsoft authorization code flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow)

## 에이전트 JWT identity mapping

다음은 **delegated JWT 모드** 설정입니다. 로컬 agent_key와 무인 agent 모드는 [AISG 가이드](aisg.md)를 참조하세요.

Broker 모드는 외부 IdP가 발급한 JWT의 issuer, audience, scope를 검증한 뒤 `identity_claims`에 명시된 값만 tenant, user, agent, delegation, task identity로 변환합니다. 임의 claim이나 gateway token은 검사 증거나 대상 서비스로 전달하지 않습니다. 필수 claim이 없거나 broker tenant와 다르면 fail closed 합니다. Entra, Okta, Keycloak 등 호환 issuer를 사용할 수 있지만 claim 발급과 workload binding의 신뢰성은 고객이 검증해야 합니다. [셀프호스팅](self-hosting.md) · [보안](security.md)
