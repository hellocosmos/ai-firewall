"""Console pool authorization and cross-process policy snapshots."""
from fastapi.testclient import TestClient
import pytest
from asr_proxy.console.app import create_app
from asr_proxy.console.runtime import Runtime
from asr_proxy.console.dataplane import StreamInspection
from asr_proxy.console.network import NetworkConfig
HEADERS={'origin':'http://127.0.0.1:5176','x-td-demo':'1'}


def test_pool_controls_require_admin_and_csrf(tmp_path,monkeypatch):
  app=create_app(tmp_path);calls=[]
  monkeypatch.setattr(app.state.runtime,'inspector_control',lambda *args:calls.append(args) or {'state':'stopped'})
  with TestClient(app) as client:
    assert client.post('/demo-api/inspectors',headers=HEADERS,json={'action':'stop'}).status_code==401
    viewer=app.state.runtime.store.create_session({'username':'viewer','role':'viewer','authentication':'local'})
    client.cookies.set('td_demo_session',viewer)
    assert client.post('/demo-api/inspectors',headers=HEADERS,json={'action':'stop'}).status_code==403
    client.cookies.clear();client.headers.update(HEADERS)
    assert client.post('/demo-api/login',json={'username':'admin','password':'1234'}).status_code==200
    assert client.post('/demo-api/inspectors',headers={'origin':'https://invalid.test'},json={'action':'stop'}).status_code==403
    assert client.post('/demo-api/inspectors',json={'action':'apply','replicas':3}).status_code==422
    assert calls==[]
    assert client.post('/demo-api/inspectors',json={'action':'apply','replicas':2}).status_code==200
    assert calls==[('apply',2)]


def test_new_stream_refreshes_policy_without_changing_existing_stream(tmp_path):
  manager=Runtime(tmp_path);worker=Runtime(tmp_path);old=StreamInspection(worker)
  policy=manager.policy();policy['rules']['notes.read']='block';manager.apply(policy)
  new=StreamInspection(worker)
  assert old.policy['rules']['notes.read']=='allow'
  assert new.policy['rules']['notes.read']=='block'
  assert old.engine is not new.engine
  assert new.engine.config.routes[0].tools['notes.read'].effect=='block'


def test_reserved_pool_ports():
  for port in (18101,18104,18111,18114):
    with pytest.raises(ValueError):NetworkConfig(listen_port=port)


def test_apply_failure_restores_previous_pool(tmp_path,monkeypatch):
  runtime=Runtime(tmp_path);calls=[]
  monkeypatch.setattr(runtime.workers,'stop',lambda:calls.append('stop'))
  def start(n):
    calls.append(n)
    if n==4:raise ValueError('synthetic startup failure')
  monkeypatch.setattr(runtime.workers,'start',start)
  monkeypatch.setattr(runtime.network,'start',lambda:None)
  with pytest.raises(ValueError):runtime.inspector_control('apply',4)
  assert calls==['stop',4,'stop',1]
  assert runtime.network.replicas==1 and runtime.store.get('inspectors') is None


def test_service_renderer_paths_and_shutdown():
  import importlib.util
  from pathlib import Path
  path=Path(__file__).parents[1]/'scripts/render-console-service.py'
  spec=importlib.util.spec_from_file_location('service_renderer',path)
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  unit=module.render('/opt/Trap Defense')
  assert 'WorkingDirectory=/opt/Trap Defense\n' in unit
  assert 'ExecStart="/opt/Trap Defense/.venv/bin/trapdefense-console"' in unit
  assert 'KillMode=control-group' in unit and 'StartLimitBurst=3' in unit
  assert 'UMask=0077' in unit and 'Restart=on-failure' in unit
  with pytest.raises(ValueError):module.render('/tmp/invalid\nunit')


def test_stale_supervisor_does_not_show_healthy_children(tmp_path):
  import json
  from types import SimpleNamespace
  runtime=Runtime(tmp_path)
  runtime.workers.directory.mkdir()
  runtime.workers.process=SimpleNamespace(pid=123,poll=lambda:1)
  (runtime.workers.directory/'status.json').write_text(json.dumps({'state':'healthy','supervisor_pid':123,'updated_at':0,'replicas':[{'state':'healthy'}]}))
  status=runtime.workers.status()
  assert status['state']=='failed' and status['replicas'][0]['state']=='unknown'
