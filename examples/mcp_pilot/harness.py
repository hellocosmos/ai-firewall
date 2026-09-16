"""Task-owned real MCP/Envoy processes with bounded startup and cleanup."""
import os
from pathlib import Path
import platform
import secrets
import socket
import subprocess
import sys
import time
from uuid import uuid4

import httpx
import yaml

from asr_proxy.console.network import IMAGE
from asr_proxy.inspection.contracts import InspectionConfig
from asr_proxy.inspection.pool import atomic_write, parser, render_envoy

ROOT = Path(__file__).resolve().parents[2]


def config(state):
  control = {name: {'action': 'protocol', 'resource': 'pilot-protocol'}
             for name in ('initialize', 'notifications/initialized', 'tools/list')}
  tools = {name: {'action': action, 'resource_pointer': '/params/arguments/document_id',
                  'effect': 'block' if action == 'delete' else 'allow'}
           for name, action in [('read_document', 'read'), ('write_document', 'write'),
                                ('delete_document', 'delete')]}
  return InspectionConfig(edition='community', trusted_sources=['pilot-adapter'],
    max_body_bytes=65536, nonce_db=str(state/'nonces.sqlite'), audit_path=str(state/'inspection.jsonl'),
    routes=[{'authority': 'pilot.test', 'path': '/mcp', 'tools': {**control, **tools},
             'redact_fields': ['/params/arguments/text']}])


def free_ports(count):
  sockets = []
  try:
    for _ in range(count):
      sock = socket.socket(); sock.bind(('127.0.0.1', 0)); sockets.append(sock)
    return [s.getsockname()[1] for s in sockets]
  finally:
    for sock in sockets: sock.close()


class Pilot:
  def __init__(self, directory):
    self.directory = Path(directory).expanduser().resolve()
    self.processes, self.logs = [], []
    self.container = 'td-mcp-pilot-' + uuid4().hex[:12]
    self.container_owned = False

  def spawn(self, name, module, *args):
    log = (self.directory/(name+'.log')).open('xb'); self.logs.append(log)
    log_path = self.directory/(name+'.log'); log_path.chmod(0o600)
    process = subprocess.Popen([sys.executable, '-m', module, *map(str, args)], cwd=ROOT,
      stdout=log, stderr=subprocess.STDOUT)
    self.processes.append(process)
    return process

  def wait(self, url, expected, seconds=25):
    deadline = time.monotonic()+seconds
    with httpx.Client(timeout=.5, trust_env=False) as client:
      while time.monotonic() < deadline:
        if any(p.poll() is not None for p in self.processes):
          raise RuntimeError('Pilot process exited; inspect private logs')
        try:
          if client.get(url).status_code == expected: return
        except httpx.HTTPError: pass
        time.sleep(.1)
    raise RuntimeError('Pilot readiness timed out; inspect private logs')

  def __enter__(self):
    self.directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    try:
      self.docker = ['docker']
      subprocess.run(self.docker+['info'], check=True, capture_output=True, timeout=15)
      subprocess.run(self.docker+['image', 'inspect', IMAGE], check=True, capture_output=True, timeout=15)
      direct, upstream, grpc, health, proxy, adapter = free_ports(6)
      self.direct_url = f'http://127.0.0.1:{direct}/mcp'
      self.protected_url = f'http://127.0.0.1:{adapter}/mcp'
      self.proxy_url = f'http://127.0.0.1:{proxy}'
      self.token = secrets.token_urlsafe(32)
      atomic_write(self.directory/'adapter.token', self.token)
      atomic_write(self.directory/'attestation.key', secrets.token_bytes(48))
      atomic_write(self.directory/'inspector.yaml', yaml.safe_dump(config(self.directory).model_dump()))
      self.spawn('direct', 'examples.mcp_pilot.server', '--database', self.directory/'direct.sqlite', '--port', direct)
      self.spawn('protected', 'examples.mcp_pilot.server', '--database', self.directory/'protected.sqlite', '--port', upstream)
      self.wait(self.direct_url, 406)
      self.wait(f'http://127.0.0.1:{upstream}/mcp', 406)
      self.inspector = self.spawn('inspector', 'asr_proxy.inspection.server',
        '--config', self.directory/'inspector.yaml', '--key-file', self.directory/'attestation.key',
        '--grpc-port', grpc, '--mirror-port', health, '--parent-pid', os.getpid())
      self.wait(f'http://127.0.0.1:{health}/_trapdefense/health', 200)
      linux = platform.system() == 'Linux'
      host = '127.0.0.1' if linux else 'host.docker.internal'
      args = parser().parse_args(['--config', 'unused', '--key-file', 'unused', '--state-directory', 'unused',
        '--envoy-output', 'unused', '--grpc-base-port', str(grpc), '--health-base-port', str(health),
        '--proxy-port', str(proxy), '--proxy-bind', '127.0.0.1' if linux else '0.0.0.0',
        '--upstream-port', str(upstream), '--upstream-address', host, '--inspector-address', host])
      output = self.directory/'envoy.yaml'
      atomic_write(output, yaml.safe_dump(render_envoy(args)), 0o644)
      network = ['--network', 'host'] if linux else ['-p', f'127.0.0.1:{proxy}:{proxy}']
      self.container_owned = True  # The unique name is ours even if docker run times out.
      subprocess.run(self.docker+['run', '-d', '--rm', '--pull=never', '--name', self.container,
        '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges', '--user', '65532:65532',
        *network, '--mount', f'type=bind,source={output},target=/etc/envoy/pilot.yaml,readonly',
        '--entrypoint', '/usr/local/bin/envoy', IMAGE, '--concurrency', '2', '--log-level', 'error',
        '-c', '/etc/envoy/pilot.yaml'], check=True, capture_output=True, timeout=20)
      self.wait(self.proxy_url+'/mcp', 403)
      self.spawn('adapter', 'examples.mcp_pilot.adapter', '--proxy', self.proxy_url, '--port', adapter,
        '--key-file', self.directory/'attestation.key', '--token-file', self.directory/'adapter.token')
      self.wait(self.protected_url, 405)
      return self
    except BaseException:
      self.__exit__(None, None, None)
      raise

  def stop_inspector(self):
    self.inspector.terminate()
    self.inspector.wait(timeout=10)

  def __exit__(self, *_):
    for process in reversed(self.processes):
      if process.poll() is None:
        process.terminate()
        try: process.wait(timeout=8)
        except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=3)
    if self.container_owned:
      subprocess.run(self.docker+['rm', '-f', self.container], capture_output=True, timeout=15)
    for log in self.logs: log.close()
