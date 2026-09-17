"""Loopback-only MCP gateway fixture for an actual VS Code compatibility run."""
import argparse
import json
from pathlib import Path

import httpx
import uvicorn

from asr_proxy.selfhost.config import Deployment,load
from asr_proxy.selfhost.gateway import create_gateway


ROOT=Path(__file__).parents[2]
CLIENT_KEY='synthetic-client-'+'x'*32
SIGNING_KEY=b'synthetic-signing-key-'+b'x'*32


def prepare_workspace(workspace: Path,port: int):
  config=workspace/'.vscode/mcp.json'
  config.parent.mkdir(parents=True,exist_ok=True)
  config.write_text(json.dumps({'servers':{'trapdefense-compat':{
    'type':'http','url':f'http://127.0.0.1:{port}/mcp',
    'headers':{'X-TD-Client-Key':CLIENT_KEY},
  }}},indent=2)+'\n')
  (workspace/'README.md').write_text(
    '# TrapDefense VS Code compatibility workspace\n\n'
    'Open **MCP: List Servers**, start `trapdefense-compat`, and verify that it reports running.\n'
    'This workspace and its credentials are synthetic and loopback-only.\n')


def app(receipt_path: Path):
  data=load(ROOT/'deploy/selfhost/deployment.yaml').model_dump(exclude_none=True)
  data['target_auth']={'mode':'none'}
  for route in data['routes']:
    if route['protocol']=='mcp':
      route['tools']['notes_read']=route['tools'].pop('notes.read')
  config=Deployment.model_validate(data)

  def target(request):
    payload=json.loads(request.content)
    with receipt_path.open('a') as handle:
      handle.write(json.dumps({'method':payload.get('method'),'protocol':
        request.headers.get('mcp-protocol-version'),'requested_protocol':
        payload.get('params',{}).get('protocolVersion')},sort_keys=True)+'\n')
    method=payload.get('method')
    if method=='initialize':
      body={'jsonrpc':'2.0','id':payload['id'],'result':{'protocolVersion':'2025-11-25',
        'capabilities':{'tools':{}},
        'serverInfo':{'name':'trapdefense-vscode-lab','version':'0.39'}}}
    elif method=='notifications/initialized':
      return httpx.Response(202,headers={'content-type':'application/json'},stream=httpx.ByteStream(b''))
    elif method=='tools/list':
      body={'jsonrpc':'2.0','id':payload['id'],'result':{'tools':[
        {'name':'notes_read','description':'Read a synthetic compatibility note',
         'inputSchema':{'type':'object','properties':{}}}]}}
    elif method=='tools/call':
      body={'jsonrpc':'2.0','id':payload['id'],'result':{'content':[
        {'type':'text','text':'Synthetic TrapDefense compatibility result'}]}}
    else:
      body={'jsonrpc':'2.0','id':payload.get('id'),'error':{'code':-32601,'message':'Method not found'}}
    return httpx.Response(200,headers={'content-type':'application/json'},
      stream=httpx.ByteStream(json.dumps(body).encode()))

  return create_gateway(config,CLIENT_KEY,SIGNING_KEY,transport=httpx.MockTransport(target))


def main():
  parser=argparse.ArgumentParser()
  parser.add_argument('--port',type=int,default=19184)
  parser.add_argument('--receipts',type=Path,required=True)
  parser.add_argument('--workspace',type=Path)
  args=parser.parse_args()
  args.receipts.parent.mkdir(parents=True,exist_ok=True)
  args.receipts.write_text('')
  if args.workspace:
    prepare_workspace(args.workspace,args.port)
    print(f'VS Code workspace: {args.workspace.resolve()}')
    print('Start trapdefense-compat from MCP: List Servers, then inspect the receipt file.')
  uvicorn.run(app(args.receipts),host='127.0.0.1',port=args.port,log_level='warning')


if __name__=='__main__':main()
