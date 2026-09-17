"""Same-host Community inspector supervision; never launches or replays tool traffic."""
from __future__ import annotations

import argparse
import copy
import fcntl
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import yaml

from .contracts import InspectionConfig


class PoolError(ValueError):
  """Fixed, non-sensitive configuration failure code."""


def atomic_write(path: Path, content: str | bytes, mode: int = 0o600):
  descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f'.{path.name}-')
  try:
    with os.fdopen(descriptor, 'wb') as stream:
      os.fchmod(stream.fileno(), mode)
      stream.write(content.encode() if isinstance(content, str) else content)
    os.replace(temporary, path)
  finally:
    Path(temporary).unlink(missing_ok=True)


def port_sets(args):
  grpc_ports = list(range(args.grpc_base_port, args.grpc_base_port + args.replicas))
  health_ports = list(range(args.health_base_port, args.health_base_port + args.replicas))
  ports = grpc_ports + health_ports + [args.proxy_port]
  if len(set(ports)) != len(ports) or any(not 1024 <= port <= 65535 for port in ports):
    raise PoolError('pool_ports_must_be_distinct_and_unprivileged')
  if not 1 <= args.upstream_port <= 65535 or not args.upstream_address.strip():
    raise PoolError('pool_requires_valid_upstream')
  return grpc_ports, health_ports


def render_envoy(args):
  grpc_ports, health_ports = port_sets(args)
  template = Path(__file__).parents[1] / 'console' / 'envoy-inline.yaml'
  config = yaml.safe_load(template.read_text())
  listener = config['static_resources']['listeners'][0]
  listener['address']['socket_address']['address'] = args.proxy_bind
  listener['address']['socket_address']['port_value'] = args.proxy_port
  for cluster in config['static_resources']['clusters']:
    group = cluster['load_assignment']['endpoints'][0]
    endpoint = group['lb_endpoints'][0]
    if cluster['name'] == 'trapdefense_inspector':
      group['lb_endpoints'] = []
      for port, health_port in zip(grpc_ports, health_ports):
        member = copy.deepcopy(endpoint)
        member['endpoint']['address']['socket_address'] = {
          'address': args.inspector_address, 'port_value': port}
        member['endpoint']['health_check_config'] = {'port_value': health_port}
        group['lb_endpoints'].append(member)
      cluster['lb_policy'] = 'ROUND_ROBIN'
      cluster['common_lb_config'] = {'healthy_panic_threshold': {'value': 0}}
      cluster['health_checks'] = [{'timeout': '1s', 'interval': '1s',
        'unhealthy_threshold': 1, 'healthy_threshold': 1,
        'http_health_check': {'path': '/_trapdefense/health', 'codec_client_type': 'HTTP1'}}]
    else:
      endpoint['endpoint']['address']['socket_address'] = {
        'address': args.upstream_address, 'port_value': args.upstream_port}
  return config


class InspectorPool:
  def __init__(self, args):
    self.args = args
    self.grpc_ports, self.health_ports = port_sets(args)
    self.members = []
    self.stopping = False
    self.client = httpx.Client(timeout=.4, trust_env=False)
    self.state = Path(args.state_directory).resolve()

  def stop(self, *_):
    self.stopping = True

  def status(self, state, reason=None):
    atomic_write(self.state / 'status.json', json.dumps({
      'state': state, 'reason': reason, 'supervisor_pid': os.getpid(), 'updated_at': time.time(),
      'replicas': [{'index': i, 'pid': m['process'].pid, 'state': m['state'],
        'grpc_port': self.grpc_ports[i], 'health_port': self.health_ports[i],
        'restarts': m['restarts']} for i, m in enumerate(self.members)],
    }, indent=2) + '\n')

  def spawn(self, index, restarts=0):
    log_path = self.state / f'inspector-{index}.log'
    fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'ab') as log:
      process = subprocess.Popen([sys.executable, '-m', 'asr_proxy.inspection.server',
        '--config', str(self.snapshot / 'config.yaml'), '--key-file', str(self.snapshot / 'key'),
        '--grpc-port', str(self.grpc_ports[index]), '--mirror-port', str(self.health_ports[index]),
        '--parent-pid', str(os.getpid())], stdout=log, stderr=subprocess.STDOUT)
    return {'process': process, 'restarts': restarts, 'state': 'starting',
      'started': time.monotonic(), 'misses': 0, 'retry_at': None}

  def healthy(self, index):
    try:
      response = self.client.get(f'http://127.0.0.1:{self.health_ports[index]}/_trapdefense/health')
      with socket.create_connection(('127.0.0.1', self.grpc_ports[index]), timeout=.2):
        return response.status_code == 200
    except (httpx.HTTPError, OSError):
      return False

  @staticmethod
  def terminate(member):
    process = member['process']
    if process.poll() is None:
      process.terminate()
      try:
        process.wait(timeout=5)
      except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)
    member['state'] = 'stopped'

  def monitor(self):
    while not self.stopping:
      for index, member in enumerate(self.members):
        now = time.monotonic()
        if member['retry_at'] is not None:
          if now >= member['retry_at']:
            self.members[index] = self.spawn(index, member['restarts'] + 1)
          continue
        if member['process'].poll() is None and self.healthy(index):
          member['state'], member['misses'] = 'healthy', 0
          continue
        member['misses'] += 1
        starting = member['state'] == 'starting' and now - member['started'] < 15
        if member['process'].poll() is None and (starting or member['misses'] < 3):
          member['state'] = 'starting' if starting else 'unhealthy'
          continue
        self.terminate(member)
        if member['restarts'] >= self.args.max_restarts:
          raise RuntimeError('pool_recovery_exhausted')
        member['state'] = 'restarting'
        member['retry_at'] = time.monotonic() + min(2 ** member['restarts'], 8)
      self.status('healthy' if all(m['state'] == 'healthy' for m in self.members) else 'degraded')
      time.sleep(.25)

  def run(self):
    config = InspectionConfig.model_validate(yaml.safe_load(Path(self.args.config).read_text()))
    key_path = Path(self.args.key_file).resolve()
    key = key_path.read_bytes()
    if key_path.stat().st_mode & 0o077 or len(key) < 32:
      raise PoolError('pool_requires_private_attestation_key')
    for field in ('nonce_db', 'audit_path', 'broker_store'):
      setattr(config, field, str(Path(getattr(config, field)).resolve()))
    output = Path(self.args.envoy_output).resolve()
    protected = {Path(self.args.config).resolve(), key_path, Path(config.nonce_db),
                 Path(config.audit_path), Path(config.broker_store), self.state / 'status.json',
                 self.state / 'pool.lock'}
    if output in protected:
      raise PoolError('envoy_output_overlaps_security_state')
    self.state.mkdir(mode=0o700, parents=True, exist_ok=True)
    if self.state.stat().st_mode & 0o077:
      raise PoolError('pool_state_directory_must_be_private')
    fd = os.open(self.state / 'pool.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
      try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
      except BlockingIOError:
        raise PoolError('pool_already_running') from None
      sockets = []
      try:
        for port in self.grpc_ports + self.health_ports:
          listener = socket.socket()
          sockets.append(listener)
          # A recently closed health listener may leave TIME_WAIT connections.
          # Reuse closed sockets, but listen() still rejects an active owner.
          listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
          listener.bind(('127.0.0.1', port))
          listener.listen(1)
      finally:
        for listener in sockets:
          listener.close()
      with tempfile.TemporaryDirectory(prefix='snapshot-', dir=self.state) as temporary:
        self.snapshot = Path(temporary)
        atomic_write(self.snapshot / 'config.yaml', yaml.safe_dump(config.model_dump()))
        atomic_write(self.snapshot / 'key', key)
        output.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(output, yaml.safe_dump(render_envoy(self.args)), 0o644)
        try:
          for index in range(self.args.replicas):
            self.members.append(self.spawn(index))
          self.status('starting')
          self.monitor()
        finally:
          for member in self.members:
            self.terminate(member)
          self.status('stopped' if self.stopping else 'failed',
                      None if self.stopping else 'pool_startup_or_recovery_failed')
          self.client.close()


def parser():
  value = argparse.ArgumentParser(description='Supervise 1, 2 or 4 same-host TrapDefense inspectors')
  value.add_argument('--config', required=True)
  value.add_argument('--key-file', required=True)
  value.add_argument('--state-directory', required=True)
  value.add_argument('--envoy-output', required=True)
  value.add_argument('--replicas', type=int, choices=(1, 2, 4), default=1)
  value.add_argument('--grpc-base-port', type=int, default=18101)
  value.add_argument('--health-base-port', type=int, default=18111)
  value.add_argument('--proxy-port', type=int, default=18082)
  value.add_argument('--proxy-bind', choices=('127.0.0.1', '0.0.0.0'), default='127.0.0.1')
  value.add_argument('--inspector-address', choices=('127.0.0.1', 'host.docker.internal'), default='127.0.0.1')
  value.add_argument('--upstream-address', default='127.0.0.1')
  value.add_argument('--upstream-port', type=int, default=18090)
  value.add_argument('--max-restarts', type=int, choices=range(0, 11), default=3)
  return value


def main():
  pool = None
  try:
    pool = InspectorPool(parser().parse_args())
    signal.signal(signal.SIGTERM, pool.stop)
    signal.signal(signal.SIGINT, pool.stop)
    pool.run()
  except PoolError as exc:
    print(str(exc), file=sys.stderr)
    raise SystemExit(1) from None
  except (ValueError, OSError, RuntimeError, yaml.YAMLError):
    print('Inspector pool failed; check private state/status.json and inspector logs.', file=sys.stderr)
    raise SystemExit(1) from None
  finally:
    if pool is not None:
      pool.client.close()


if __name__ == '__main__':
  main()
