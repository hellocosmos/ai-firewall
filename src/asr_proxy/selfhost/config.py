"""Fixed-destination configuration. No client-controlled upstream selection."""
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
import ipaddress
import re
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator
from asr_proxy.inspection.contracts import RouteRule


class Deployment(BaseModel):
  model_config = ConfigDict(extra='forbid')
  upstream: str
  allow_plaintext_upstream: bool = False
  console_origin: str = 'http://localhost:18080'
  destination_auth: Literal['passthrough', 'static_bearer'] = 'passthrough'
  bearer_file: str | None = None
  max_body_bytes: int = Field(default=1048576, ge=1024, le=1048576)
  routes: list[RouteRule] = Field(min_length=1, max_length=100)

  @model_validator(mode='after')
  def validate_contract(self):
    target = urlsplit(self.upstream)
    if (target.scheme not in ('http', 'https') or not target.hostname or target.username or target.password
        or target.path not in ('', '/') or target.query or target.fragment):
      raise ValueError('upstream must be an HTTP(S) origin without credentials, path or query')
    if not re.fullmatch(r'[a-zA-Z0-9.-]+', target.hostname):
      raise ValueError('Use a DNS hostname or IPv4 upstream')
    if target.scheme == 'http' and not self.allow_plaintext_upstream:
      raise ValueError('HTTP requires allow_plaintext_upstream for a trusted network')
    if target.scheme == 'https':
      try: ipaddress.ip_address(target.hostname)
      except ValueError: pass
      else: raise ValueError('HTTPS requires a DNS hostname for certificate verification')
    if target.port is not None and not 1 <= target.port <= 65535:
      raise ValueError('Invalid upstream port')
    origin = urlsplit(self.console_origin)
    if (origin.scheme not in ('http', 'https') or not origin.hostname or origin.username or origin.password
        or origin.path or origin.query or origin.fragment):
      raise ValueError('console_origin must be an exact HTTP(S) origin')
    if (self.destination_auth == 'static_bearer') != bool(self.bearer_file):
      raise ValueError('static_bearer requires bearer_file; passthrough must not set it')
    seen = set()
    for route in self.routes:
      if route.authority != target.netloc:
        raise ValueError('Every route authority must equal the fixed upstream authority')
      if (not re.fullmatch(r'/[A-Za-z0-9_./~-]*', route.path) or '..' in route.path.split('/')
          or '//' in route.path or route.method not in ('GET','POST','PUT','PATCH','DELETE','HEAD')):
        raise ValueError('Routes require unambiguous exact paths and supported HTTP methods')
      pair = (route.method, route.path)
      if pair in seen: raise ValueError('Duplicate method/path mapping')
      seen.add(pair)
      if route.protocol == 'mcp' and route.method != 'POST':
        raise ValueError('This profile supports stateless MCP JSON POST only')
      rules = route.tools if route.protocol == 'mcp' else {route.tool: route.rule}
      if not rules or any(rule is None for rule in rules.values()):
        raise ValueError('Explicit tool/action rules are required')
      if any(not rule.resource and not rule.resource_pointer for rule in rules.values()):
        raise ValueError('Every rule requires a resource mapping')
    return self

  def entries(self):
    for index, route in enumerate(self.routes):
      rules = route.tools if route.protocol == 'mcp' else {route.tool: route.rule}
      for name, rule in rules.items():
        yield f'{index}:{name}', name, rule

  def public(self):
    return {'upstream': self.upstream, 'console_origin': self.console_origin,
      'destination_auth': self.destination_auth, 'source': 'selfhost-adapter',
      'max_body_bytes': self.max_body_bytes,
      'routes': [{'method': r.method, 'path': r.path, 'protocol': r.protocol,
                  'tools': list(r.tools) if r.protocol == 'mcp' else [r.tool]} for r in self.routes]}


def load(path):
  return Deployment.model_validate(yaml.safe_load(Path(path).read_text()))


def envoy_config(config):
  template = Path(__file__).parents[1] / 'console/envoy-inline.yaml'
  value = yaml.safe_load(template.read_text())
  clusters = value['static_resources']['clusters']
  def socket(cluster):
    return cluster['load_assignment']['endpoints'][0]['lb_endpoints'][0]['endpoint']['address']['socket_address']
  socket(clusters[0]).update(address='app', port_value=18081)
  target = urlsplit(config.upstream)
  socket(clusters[1]).update(address=target.hostname, port_value=target.port or (443 if target.scheme=='https' else 80))
  if target.scheme == 'https':
    clusters[1]['transport_socket'] = {'name':'envoy.transport_sockets.tls','typed_config':{
      '@type':'type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.UpstreamTlsContext',
      'sni':target.hostname,'common_tls_context':{'validation_context':{
        'trusted_ca':{'filename':'/etc/ssl/certs/ca-certificates.crt'},
        'match_typed_subject_alt_names':[{'san_type':'DNS','matcher':{'exact':target.hostname}}]}}}}
  listener = value['static_resources']['listeners'][0]
  listener['per_connection_buffer_limit_bytes'] = config.max_body_bytes
  return yaml.safe_dump(value, sort_keys=False)
