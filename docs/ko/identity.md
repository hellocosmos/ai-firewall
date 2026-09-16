# Microsoft Entra ID — Community console SSO

[English](../en/identity.md) · [한국어](../ko/identity.md) · [简体中文](../zh-CN/identity.md) · [日本語](../ja/identity.md) · [Español](../es/identity.md) · [Français](../fr/identity.md)

Community는 단일 테넌트 Microsoft Entra ID 콘솔 SSO와 관리자·조회자 역할을 제공합니다. 콘솔 인증은 에이전트 실행 권한이 아니며 위임·승인은 Enterprise 기능입니다.

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
