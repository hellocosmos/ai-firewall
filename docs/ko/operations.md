# 동일 서버 운영 — 0.34

[English](../en/operations.md) · [한국어](../ko/operations.md) · [简体中文](../zh-CN/operations.md) · [日本語](../ja/operations.md) · [Español](../es/operations.md) · [Français](../fr/operations.md)

Connections / System에서 PID·상태·재시작 횟수를 확인합니다. 관리자는 Settings → Inspector processes에서 1·2·4개를 선택하고 적용/시작/중지할 수 있습니다. Viewer는 조회만 가능합니다. 중지 중에는 인라인 트래픽이 차단됩니다.

모든 콘솔 검사 프로세스는 로컬 정책·이벤트·재전송 방지 저장소를 공유합니다. 새 요청부터 저장된 정책을 사용하고, 진행 중 요청은 응답까지 기존 정책을 유지합니다. 프로세스 수 변경 시 검사기와 Envoy가 잠시 중단됩니다. 실패하면 이전 구성을 복원하며 복원 실패 시 차단을 유지합니다. 도구 요청을 자동 재시도하지 않습니다.

자식 프로세스당 재시작 3회 후 복구 한도를 초과하면 전체 풀이 중지됩니다. 콘솔 서비스 재시작 시 풀도 다시 시작하므로 중지는 영구 유지보수 설정이 아닙니다. 독립 CLI 풀은 콘솔 정책을 읽지 않으며 YAML/키 변경 후 전체 재시작이 필요합니다.

Linux 사용자 systemd와 기존 Docker 권한이 필요합니다. sudo 없이 설치 사용자로 실행하세요. 설치는 즉시 시작하며 제거해도 데이터는 보존합니다. 기존 콘솔을 먼저 중지하세요.

```bash
./scripts/console-service.sh install
./scripts/console-service.sh status
./scripts/console-service.sh logs
./scripts/console-service.sh restart
./scripts/console-service.sh stop
./scripts/console-service.sh start
./scripts/console-service.sh remove
```

사용자 서비스 활성화만으로 무인 부팅이 보장되지 않습니다. Docker와 사용자 관리자(linger)는 호스트 관리자가 별도로 설정해야 합니다. Ubuntu 26.04 x86_64 랩에서 Python 3.12·Node 22·Docker 설치, linger 설정 후 실제 재부팅과 SSH 로그인 전 자동 시작, 검사기 2개·정책·이벤트 보존, 합성 허용·차단·마스킹을 검증했습니다. 다른 호스트와 운영 용량은 별도 검증 대상입니다. 사용자 관리자의 Docker 그룹 반영 문제는 영문 가이드를 참고하세요. 서버 간 HA는 미구현입니다. SQLite를 네트워크 파일시스템으로 공유하지 마세요. 합성 테스트는 운영 인증이 아닙니다.

[English reference](../en/operations.md) · [Inspector pool](inspector-pool.md)
