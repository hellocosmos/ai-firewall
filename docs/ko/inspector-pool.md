# Community 검사기 다중 프로세스

[English](../en/inspector-pool.md) · [한국어](../ko/inspector-pool.md) · [简体中文](../zh-CN/inspector-pool.md) · [日本語](../ja/inspector-pool.md) · [Español](../es/inspector-pool.md) · [Français](../fr/inspector-pool.md)

같은 서버에서 검사기를 1·2·4개 실행하고 Envoy 연결 설정을 생성합니다. Docker나 콘솔을 자동 실행·교체하지 않습니다. Enterprise 및 서버 간 HA는 지원 범위 밖입니다.

모든 검사기는 같은 로컬 재전송 방지 DB와 감사 로그를 공유합니다. 프로세스별 DB 분리나 네트워크 파일시스템 사용은 금지합니다. 정책의 상대 경로는 실행 디렉터리 기준입니다. 정책·키는 시작 시 스냅샷으로 고정되므로 변경하려면 전체 풀을 재시작하고 Envoy 설정 및 서명 송신 측도 맞춰야 합니다.

장애 프로세스는 기본 최대 3회 재시작합니다. 복구 횟수를 소진하면 전체 풀이 종료됩니다. 실패한 요청을 자동 재전송하지 않으며 모든 검사기가 중단되면 우회하지 않고 오류를 반환합니다.

status.json에는 상태·PID·포트·재시작 횟수가 기록됩니다. 상태 디렉터리는 0700, 키는 소유자 전용 권한이어야 합니다. 관리 프로세스 강제 종료 시 자식도 종료하지만 상태 파일과 비공개 스냅샷은 남을 수 있으므로 PID·시간·실제 상태를 확인해야 합니다.

포트는 기본 gRPC 18101부터, 상태 확인 18111부터, 프록시 18082입니다. Docker Desktop에서는 아래 추가 옵션과 호스트 루프백 포트 게시가 필요합니다. Linux에서는 기본 설정과 Docker host network를 사용합니다. 콘솔 UI 및 서비스 관리자 연동은 이번 범위에 포함되지 않습니다.

```bash
.venv/bin/trapdefense-inspector-pool \
  --config "$PWD/.runtime-state/pool-demo/inspector.yaml" \
  --key-file "$PWD/.runtime-state/pool-demo/attestation.key" \
  --state-directory "$PWD/.runtime-state/pool-supervisor" \
  --envoy-output "$PWD/.runtime-state/pool-envoy.yaml" \
  --replicas 2
```

```text
--proxy-bind 0.0.0.0 --inspector-address host.docker.internal --upstream-address host.docker.internal
```

[Complete setup and limits / English](../en/inspector-pool.md)
