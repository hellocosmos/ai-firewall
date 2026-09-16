#!/usr/bin/env bash
# Opt-in Linux user service. Never grants Docker privileges or enables lingering.
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
action="${1:-status}"
[ "$(uname -s)" = Linux ] || { echo 'Linux with a user systemd session is required.' >&2; exit 1; }
command -v systemctl >/dev/null
unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
unit_file="$unit_dir/trapdefense-console.service"
case "$action" in
  install)
    [ -x "$repo_dir/.venv/bin/trapdefense-console" ] && [ -f "$repo_dir/console/dist/index.html" ] || { echo 'Run scripts/install-console.sh first.' >&2; exit 1; }
    docker info >/dev/null
    [ ! -e "$unit_file" ] || { echo 'Service already exists. Remove it explicitly before reinstalling.' >&2; exit 1; }
    mkdir -p "$unit_dir"
    unit_candidate="$(mktemp "$unit_dir/.trapdefense-console.XXXXXX")"
    trap 'rm -f -- "$unit_candidate"' EXIT
    "$repo_dir/.venv/bin/python" "$repo_dir/scripts/render-console-service.py" "$repo_dir" > "$unit_candidate"
    chmod 600 "$unit_candidate"
    ln "$unit_candidate" "$unit_file"
    rm -- "$unit_candidate"
    trap - EXIT
    systemctl --user daemon-reload
    systemctl --user enable --now trapdefense-console.service
    ;;
  start|stop|restart|status) systemctl --user "$action" trapdefense-console.service ;;
  logs) journalctl --user -u trapdefense-console.service -n 100 --no-pager ;;
  remove)
    systemctl --user disable --now trapdefense-console.service
    rm -- "$unit_file"
    systemctl --user daemon-reload
    echo 'Service removed. Persistent console state was preserved.'
    ;;
  *) echo 'Usage: console-service.sh install|start|stop|restart|status|logs|remove' >&2; exit 2 ;;
esac
