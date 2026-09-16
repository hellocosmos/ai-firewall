# 기존 SDK에서 이전하기

[English](../en/migration.md) · [한국어](../ko/migration.md) · [简体中文](../zh-CN/migration.md) · [日本語](../ja/migration.md) · [Español](../es/migration.md) · [Français](../fr/migration.md)

기존 내장형 Python SDK와 이력은 [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security)에 유지됩니다. 이 저장소는 새로운 Community 프록시 제품입니다. SDK 호환이나 자동 패키지 이전을 제공하지 않습니다.

1. 보호할 HTTP/MCP 호출과 목적지를 식별합니다.
2. TLS 복호화 뒤에 신뢰할 수 있는 서명 어댑터를 두고 프록시 경유를 강제합니다.
3. 도구·행위 매핑, 제한값, 마스킹 필드를 명시합니다.
4. 합성 데이터로 관찰한 뒤 inline 허용·마스킹·차단·장애 동작을 확인합니다.
5. 위임 접근과 요청 단위 승인이 필요할 때 비공개 Enterprise 제공자를 추가합니다.

기존 SDK 사용자는 고정 버전을 유지하면서 별도 경로로 파일럿을 평가할 수 있습니다. [콘솔 안내](console.md)에서 시작하세요. 소스 설치는 PyPI 배포나 고객 환경 업그레이드를 의미하지 않습니다. 버전 변경 전에 상태를 백업하고 합성 환경의 자격 증명이나 서명 키를 운영에 복사하지 마세요.
