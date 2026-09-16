"""Synthetic JSON HTTP/MCP destination for the opt-in smoke profile only."""
import json
import os
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
  def log_message(self, *args):pass
  def do_POST(self):
    if self.headers.get('Transfer-Encoding','').lower()=='chunked':
      chunks=[]
      while True:
        size=int(self.rfile.readline().strip().split(b';')[0],16)
        if not size:
          self.rfile.readline();break
        chunks.append(self.rfile.read(size));self.rfile.read(2)
      raw=b''.join(chunks)
    else:raw=self.rfile.read(int(self.headers.get('Content-Length','0')))
    value=json.loads(raw)
    if self.headers.get('Authorization')!='Bearer synthetic-target-token':
      self.send_response(401);self.send_header('Content-Length','0');self.end_headers();return
    if any(name.lower().startswith(('x-td-','x-asr-')) for name in self.headers):
      self.send_response(500);self.send_header('Content-Length','0');self.end_headers();return
    if self.path=='/mcp':
      value={'jsonrpc':'2.0','id':value.get('id'), 'result':{'content':[{'type':'text','text':json.dumps(value.get('params',{}).get('arguments',{}))}]}}
    data=json.dumps({'received':value} if self.path!='/mcp' else value).encode()
    self.send_response(200);self.send_header('Content-Type','application/json')
    self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)


server=ThreadingHTTPServer(('0.0.0.0',8080),Handler)
if os.environ.get('TD_FIXTURE_CERT'):
  context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
  context.load_cert_chain(os.environ['TD_FIXTURE_CERT'],os.environ['TD_FIXTURE_KEY'])
  server.socket=context.wrap_socket(server.socket,server_side=True)
server.serve_forever()
