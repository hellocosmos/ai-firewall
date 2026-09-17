"""Pool configuration cannot weaken transport or shared security state."""
from pathlib import Path

import pytest
import yaml

from asr_proxy.inspection.demo import init_demo
from asr_proxy.inspection.pool import InspectorPool, atomic_write, parser, port_sets, render_envoy


def arguments(tmp_path, *extra):
  return parser().parse_args(['--config', str(tmp_path/'config.yaml'), '--key-file', str(tmp_path/'key'),
    '--state-directory', str(tmp_path/'pool'), '--envoy-output', str(tmp_path/'envoy.yaml'), *extra])


@pytest.mark.parametrize('count', [1, 2, 4])
def test_render_keeps_fail_closed_and_per_replica_health(tmp_path, count):
  args = arguments(tmp_path, '--replicas', str(count))
  result = render_envoy(args)
  assert result['static_resources']['listeners'][0]['address']['socket_address']['address'] == '127.0.0.1'
  cluster = result['static_resources']['clusters'][0]
  endpoints = cluster['load_assignment']['endpoints'][0]['lb_endpoints']
  assert [e['endpoint']['address']['socket_address']['port_value'] for e in endpoints] == list(range(18101, 18101+count))
  assert [e['endpoint']['health_check_config']['port_value'] for e in endpoints] == list(range(18111, 18111+count))
  assert cluster['common_lb_config']['healthy_panic_threshold']['value'] == 0
  hcm = result['static_resources']['listeners'][0]['filter_chains'][0]['filters'][0]['typed_config']
  extproc = hcm['http_filters'][0]['typed_config']
  assert extproc['failure_mode_allow'] is False
  assert extproc['message_timeout'] == '2s'
  assert 'retry_policy' not in hcm['route_config']['virtual_hosts'][0]['routes'][0]['route']


@pytest.mark.parametrize('extra', [('--grpc-base-port','18111'), ('--health-base-port','65535','--replicas','4'),
                                  ('--proxy-port','18101'), ('--grpc-base-port','80')])
def test_ports_cannot_overlap_or_overflow(tmp_path, extra):
  with pytest.raises(ValueError): port_sets(arguments(tmp_path, *extra))


def test_atomic_key_snapshot_preserves_binary_bytes_and_permissions(tmp_path):
  target = tmp_path/'key'
  key = bytes(range(256))
  atomic_write(target, key)
  assert target.read_bytes() == key
  assert target.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize('problem', ['insecure_key', 'overlapping_output'])
def test_invalid_pool_configuration_never_spawns(tmp_path, monkeypatch, problem):
  demo = tmp_path/'demo'; init_demo(demo)
  args = arguments(tmp_path)
  args.config = str(demo/'inspector.yaml'); args.key_file = str(demo/'attestation.key')
  if problem == 'insecure_key': Path(args.key_file).chmod(0o644)
  else: args.envoy_output = args.key_file
  pool = InspectorPool(args)
  monkeypatch.setattr(pool, 'spawn', lambda *args: pytest.fail('invalid configuration spawned a child'))
  try:
    with pytest.raises(ValueError): pool.run()
  finally: pool.client.close()
