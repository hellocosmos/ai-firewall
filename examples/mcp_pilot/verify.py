"""Reproducible protocol/enforcement checks, distinct from model evidence."""
import json
import math
import sqlite3
import statistics
import time
import httpx
from .client import session, text_content
from .server import EMAIL, SECRET, EVASION


def document(path, name):
  with sqlite3.connect(path) as db:
    row=db.execute('SELECT body FROM documents WHERE id=?',(name,)).fetchone()
  return row[0] if row else None


def receipts(path):
  with sqlite3.connect(path) as db:return db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0]


def audit(pilot):
  path=pilot.directory/'inspection.jsonl'
  return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


async def invoke(url, token, tool, arguments):
  try:
    async with session(url,token) as client:
      result=await client.call_tool(tool,arguments)
      return {'ok':not result.isError,'text':text_content(result)}
  except Exception:
    return {'ok':False,'text':''}  # Verdict reasons come from audit, not exception strings.


async def measure(url, token, samples):
  values=[]
  async with session(url,token) as client:
    tools=await client.list_tools()
    assert {t.name for t in tools.tools}=={'read_document','write_document','delete_document'}
    for index in range(samples+2):
      start=time.perf_counter()
      result=await client.call_tool('read_document',{'document_id':'handbook'})
      assert not result.isError and 'Support hours' in text_content(result)
      if index>=2:values.append((time.perf_counter()-start)*1000)
  ordered=sorted(values)
  return {'samples':samples,'p50_ms':round(statistics.median(values),3),
    'p95_ms':round(ordered[math.ceil(samples*.95)-1],3),'unexpected_denials':0,
    'scope':'Sequential MCP call latency; excludes initialization, warmup and LLM inference'}


async def run_suite(pilot,samples=20):
  if not 5<=samples<=200:raise ValueError('Samples must be between 5 and 200')
  db=pilot.directory/'protected.sqlite';cases=[]
  async def check(name,tool,args,expected,phase=None,reason=None):
    before=len(audit(pilot));count=receipts(db)
    result=await invoke(pilot.protected_url,pilot.token,tool,args)
    events=audit(pilot)[before:]
    assert result['ok']==expected,name
    if reason:assert any(e['phase']==phase and e['reason']==reason for e in events),(name,events)
    if phase=='request' and not expected:assert receipts(db)==count,name
    cases.append({'case':name,'passed':True,'tool_succeeded':result['ok'],
      'downstream_executions':receipts(db)-count,'reason':reason})
    return result
  direct=await measure(pilot.direct_url,None,samples)
  protected=await measure(pilot.protected_url,pilot.token,samples)
  await check('normal_update','write_document',{'document_id':'draft','text':'Reviewed support note.'},True)
  assert document(db,'draft')=='Reviewed support note.'
  await check('delete_denied','delete_document',{'document_id':'protected'},False,'request','local_policy_denied')
  assert document(db,'protected') is not None
  baseline=await invoke(pilot.direct_url,None,'delete_document',{'document_id':'protected'})
  assert baseline['ok'] and document(pilot.directory/'direct.sqlite','protected') is None
  await check('request_pii','write_document',{'document_id':'draft','text':'Contact '+EMAIL},True,'request','pii_redacted')
  assert EMAIL not in document(db,'draft') and '[REDACTED]' in document(db,'draft')
  result=await check('response_pii','read_document',{'document_id':'customer'},True,'response','response_pii_redacted')
  assert EMAIL not in result['text'] and '[REDACTED]' in result['text']
  for name,tool,args,phase,reason in [
    ('request_secret','write_document',{'document_id':'draft','text':SECRET},'request','secret_detected'),
    ('response_secret','read_document',{'document_id':'credential'},'response','secret_detected'),
    ('response_injection','read_document',{'document_id':'injection'},'response','suspicious_instruction'),
    ('unknown_tool','unknown_document',{'document_id':'handbook'},'request','unmapped_tool')]:
    await check(name,tool,args,False,phase,reason)
  result=await check('semantic_injection_limit','read_document',{'document_id':'obfuscated'},True)
  assert EVASION in result['text'];cases[-1]['known_detection_miss']=True
  assert EMAIL not in json.dumps(audit(pilot)) and SECRET not in json.dumps(audit(pilot))
  async with httpx.AsyncClient(timeout=10,trust_env=False) as client:
    unsigned=await client.post(pilot.proxy_url+'/mcp',headers={'Host':'pilot.test'},json={
      'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'read_document','arguments':{'document_id':'handbook'}}})
    assert unsigned.status_code==403 and unsigned.json()['error']=='untrusted_or_mismatched_identity'
  cases.append({'case':'unsigned_proxy_request','passed':True})
  return {'evidence':'official_mcp_sdk_and_real_envoy_synthetic_documents','cases':cases,
    'latency':{'direct':direct,'protected':protected,'p50_delta_ms':round(protected['p50_ms']-direct['p50_ms'],3)},
    'limits':['One semantic injection fixture passed unchanged: signature coverage is incomplete.',
      'Response blocking happens after tool execution; it cannot undo side effects.',
      'Finite loopback fixture, not customer IAM, production routing or throughput certification.']}


async def verify_outage(pilot):
  count=receipts(pilot.directory/'protected.sqlite');pilot.stop_inspector()
  async with httpx.AsyncClient(timeout=10,trust_env=False) as client:
    response=await client.post(pilot.protected_url,headers={'Authorization':'Bearer '+pilot.token},json={
      'jsonrpc':'2.0','id':9,'method':'tools/call','params':{'name':'read_document','arguments':{'document_id':'handbook'}}})
  assert response.status_code>=500 and receipts(pilot.directory/'protected.sqlite')==count
  return {'case':'inspector_outage','passed':True,'http_status':response.status_code,'downstream_executions':0}
