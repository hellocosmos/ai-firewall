"""Synthetic model and MCP contracts; never represent scripted selection as real inference."""
import json
import os
import ssl
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Lock
from pathlib import Path

LOCK=Lock()
SCHEMA={'type':'object','properties':{'message':{'type':'string'}},'required':['message'],'additionalProperties':False}
TOOLS=[{'name':name,'description':description,'inputSchema':SCHEMA} for name,description in (
  ('notes_read','Read a synthetic customer note.'),('notes_delete','Delete a synthetic protected note.'))]


def receipt(kind,raw):
  with LOCK,Path('/evidence/receipts.jsonl').open('a') as stream:
    stream.write(json.dumps({'kind':kind,'pii_received':b'alex@example.com' in raw})+'\n')


def model_reply(body):
  completed=any(m['role']=='tool' for m in body['messages'])
  if completed:message={'role':'assistant','content':'Synthetic workflow complete; consult tool status for the actual outcome.'}
  else:
    delete=any('notes_delete' in m.get('content','') for m in body['messages'] if m['role']=='user')
    message={'role':'assistant','content':None,'tool_calls':[{'id':'call_synthetic_1','type':'function',
      'function':{'name':'notes_delete' if delete else 'notes_read','arguments':json.dumps({'message':'contact alex@example.com'})}}]}
  return {'id':'chatcmpl-synthetic','object':'chat.completion','created':1779123456,'model':body['model'],
    'choices':[{'index':0,'message':message,'finish_reason':'stop' if completed else 'tool_calls'}],
    'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}}


class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def do_POST(self):
    if self.headers.get('Transfer-Encoding','').lower()=='chunked':
      chunks=[]
      while True:
        size=int(self.rfile.readline().strip().split(b';')[0],16)
        if not size:self.rfile.readline();break
        chunks.append(self.rfile.read(size));self.rfile.read(2)
      raw=b''.join(chunks)
    else:raw=self.rfile.read(int(self.headers.get('Content-Length','0')))
    if len(raw)>1048576:return self.reply(413,{})
    if self.headers.get('Authorization')!='Bearer synthetic-target-only':return self.reply(401,{})
    if any(k.lower().startswith(('x-td-','x-asr-')) for k in self.headers):return self.reply(500,{})
    body=json.loads(raw)
    if self.path=='/v1/chat/completions':
      receipt('model_tool_result' if any(m['role']=='tool' for m in body['messages']) else 'model_prompt',raw)
      if body.get('stream'):
        return self.stream_reply(body)
      return self.reply(200,model_reply(body))
    if self.path!='/mcp':return self.reply(404,{})
    method=body.get('method');ident=body.get('id')
    if method=='notifications/initialized':return self.reply(202,None)
    if method=='initialize':
      result={'protocolVersion':'2025-11-25','capabilities':{'tools':{}},'serverInfo':{'name':'synthetic-workflow','version':'0.42'}}
    elif method=='tools/list':result={'tools':TOOLS}
    elif method=='tools/call':
      tool=body['params']['name']
      if tool not in ('notes_read','notes_delete'):return self.reply(400,{})
      receipt(tool,raw)
      result={'content':[{'type':'text','text':'Synthetic customer contact: alex@example.com' if tool=='notes_read' else 'Synthetic deletion executed.'}],'isError':False}
    else:return self.reply(400,{})
    self.reply(200,{'jsonrpc':'2.0','id':ident,'result':result})
  def stream_reply(self,body):
    # Delayed, split PII proves whole-stream inspection; no live provider is used.
    self.send_response(200)
    self.send_header('Content-Type','text/event-stream')
    self.send_header('Connection','close')
    self.end_headers()
    try:
      for text,finish in [('alex@',None),('example.com','stop')]:
        value={'id':'chatcmpl-synthetic','object':'chat.completion.chunk','created':1779123456,
          'model':body['model'],'choices':[{'index':0,'delta':{'content':text},'finish_reason':finish}]}
        self.wfile.write(('data: '+json.dumps(value)+'\n\n').encode());self.wfile.flush()
        time.sleep(.5)
      self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()
      receipt('model_stream_completed',b'')
    except (BrokenPipeError,ConnectionResetError):
      receipt('model_stream_disconnected',b'')
    self.close_connection=True

  def reply(self,code,value):
    raw=json.dumps(value).encode() if value is not None else b''
    self.send_response(code)
    if self.path=='/v1/chat/completions':
      self.send_header('Set-Cookie','synthetic=1779123456; HttpOnly; Secure')
      self.send_header('Set-Cookie','synthetic_second=1779123456; HttpOnly; Secure')
    self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)


if __name__=='__main__':
  tls=os.environ.get('FIXTURE_TLS')=='1'
  server=ThreadingHTTPServer(('0.0.0.0',443 if tls else 8080),Handler)
  if tls:
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain('/fixture/cert.pem','/fixture/key.pem')
    server.socket=context.wrap_socket(server.socket,server_side=True)
  server.serve_forever()
