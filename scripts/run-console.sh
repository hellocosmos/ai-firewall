#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_dir"
[ -f console/dist/index.html ] || { echo 'Run ./scripts/install-console.sh first.' >&2; exit 1; }
.venv/bin/python - <<'PY'
import socket
for port in (5176,18081,18090):
  with socket.socket() as listener:
    listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    try:listener.bind(('127.0.0.1',port))
    except OSError:raise SystemExit(f'Port {port} is occupied; no existing process was changed.')
PY
export TD_CONSOLE_ASSETS="$repo_dir/console/dist"
export TD_CONSOLE_STATE="${TD_CONSOLE_STATE:-$repo_dir/.runtime-state/console}"
exec .venv/bin/trapdefense-console
