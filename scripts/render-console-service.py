"""Render an opt-in systemd user unit; never writes system configuration."""
from pathlib import Path
import sys


def quote(value):
  if any(c in value for c in '\n\r\x00'):raise ValueError('Invalid service path')
  return '"'+value.replace('\\','\\\\').replace('"','\\"').replace('%','%%').replace('$','$$')+'"'


def render(root):
  root=Path(root).resolve()
  return '\n'.join([
    '[Unit]', 'Description=TrapDefense AI Firewall Console and Inspector Pool',
    'After=network-online.target', 'StartLimitIntervalSec=120', 'StartLimitBurst=3', '',
    '[Service]', 'Type=simple', 'WorkingDirectory='+str(root).replace('%','%%'),
    'Environment='+quote('TD_CONSOLE_ASSETS='+str(root/'console/dist')),
    'Environment='+quote('TD_CONSOLE_STATE='+str(root/'.runtime-state/console')),
    'ExecStart='+quote(str(root/'.venv/bin/trapdefense-console')),
    'Restart=on-failure', 'RestartSec=5', 'TimeoutStopSec=40', 'KillMode=control-group',
    'UMask=0077', 'NoNewPrivileges=true', '', '[Install]', 'WantedBy=default.target', '',
  ])


if __name__=='__main__':print(render(sys.argv[1]),end='')
