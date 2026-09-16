"""Persistent console policies and inspection without host Docker/process control."""
from threading import RLock
import socket
from asr_proxy.console.runtime import Runtime
from asr_proxy.console.store import Store
from asr_proxy.console.scenarios import Policy
from asr_proxy.inspection.contracts import InspectionConfig
from asr_proxy.inspection.pii import PresidioScanner


class SelfhostRuntime(Runtime):
  integrated = False  # Do not expose demo host-network or worker-management APIs.

  def __init__(self, directory, deployment, *, seed=False):
    self.deployment = deployment
    self.store = Store(directory, require_existing=True)
    self.lock = RLock()
    key_path=self.store.directory/'attestation.key'
    if key_path.stat().st_mode & 0o077:raise ValueError('Signing key permissions must be 0600')
    self.key = key_path.read_bytes()
    self.scanner = PresidioScanner()
    if self.store.get('policy') is None:
      entries = list(deployment.entries())
      self.store.set('policy',Policy(rules={key:rule.effect for key,_,rule in entries},
        pii_rules={key:rule.pii_action or 'inherit' for key,_,rule in entries}).model_dump())
    self.configure(self.policy())
    self.inspector_ready = False

  def config(self, policy):
    entries = list(self.deployment.entries())
    keys = {key for key,_,_ in entries}
    if set(policy['rules']) != keys or set(policy['pii_rules']) != keys:
      raise ValueError('Route mappings changed. Migrate the saved policy explicitly before startup.')
    routes = [route.model_copy(deep=True) for route in self.deployment.routes]
    for index, route in enumerate(routes):
      rules = route.tools if route.protocol=='mcp' else {route.tool:route.rule}
      for name, rule in rules.items():
        key = f'{index}:{name}'
        rule.effect = policy['rules'][key]
        rule.pii_action = None if policy['pii_rules'][key]=='inherit' else policy['pii_rules'][key]
    return InspectionConfig(edition='community',trusted_sources=['selfhost-adapter'],routes=routes,
      max_body_bytes=self.deployment.max_body_bytes,pii_action=policy['pii_action'],
      nonce_db=str(self.store.directory/'nonces.sqlite'),audit_path=str(self.store.directory/'inspection.jsonl'))

  def configure(self, policy):
    self.engine = self.build_engine(policy)
    self.engine_revision = policy['version']

  def stream_snapshot(self):
    with self.lock:
      policy = self.policy()
      if self.engine_revision != policy['version']:self.configure(policy)
      return self.engine, policy

  def network_status(self):
    try:
      with socket.create_connection(('envoy',18082),timeout=.3):proxy=True
    except OSError:proxy=False
    return {'inspector_ready':self.inspector_ready,'proxy_ready':proxy,
            'destination_ready':None,'probe':'listener_only'}
