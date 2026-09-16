"""Bounded no-op HTTP destination; no credentials or request bodies are persisted."""
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Lock
from uuid import uuid4
from asr_proxy.inspection.community_demo import _read_demo_body
from asr_proxy.inspection.identity import reserved_header


def create_destination(port=18090):
  lock=Lock()
  receipts={}
  class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def setup(self):super().setup();self.connection.settimeout(5)
    def log_message(self,*args):pass
    def reply(self,status,data):
      payload=json.dumps(data).encode()
      self.send_response(status)
      self.send_header('Content-Type','application/json')
      self.send_header('Content-Length',str(len(payload)))
      self.end_headers();self.wfile.write(payload)
    def do_GET(self):
      if self.path!='/_demo/stats':self.reply(404,{'error':'not_found'});return
      with lock:self.reply(200,{'count':len(receipts)})
    def do_POST(self):
      try:
        if self.path!='/mcp':raise ValueError()
        value=json.loads(_read_demo_body(self))
        params=value['params'];tool=params['name'];args=params['arguments']
        if value['method']!='tools/call' or tool not in ('notes.read','notes.delete'):raise ValueError()
        message=args.get('message','')
        if not isinstance(message,str):raise ValueError()
        receipt={'id':uuid4().hex,'tool':tool,'request_redacted':'[REDACTED]' in message,
          'reserved_headers_leaked':any(reserved_header(k.lower()) for k in self.headers)}
        with lock:
          receipts[receipt['id']]=receipt
          if len(receipts)>2000:receipts.pop(next(iter(receipts)))
        self.reply(200,{'result':{'message':'Contact alex@example.com' if args.get('demo_response_pii') else 'Synthetic tool completed'},'receipt':receipt})
      except (ValueError,KeyError,TypeError,OSError):
        self.close_connection=True
        try:self.reply(400,{'error':'invalid_synthetic_request'})
        except OSError:pass
  server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
  server.daemon_threads=True
  server.receipts=receipts
  return server
