"""Loopback-only pilot signing hop; agents never receive its attestation key."""
import argparse
from contextlib import asynccontextmanager
import hmac
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
import uvicorn

from asr_proxy.inspection.community_demo import validate_endpoint
from asr_proxy.inspection.contracts import HttpMessage
from asr_proxy.inspection.identity import sign_attestation, reserved_header, TRANSPORT_HEADERS

MAX_BYTES = 65536


def create_app(proxy_url, authority, key, access_token, *, transport=None):
  target = validate_endpoint(proxy_url)
  if authority != 'pilot.test' or len(key) < 32 or len(access_token) < 32:
    raise ValueError('Invalid pilot adapter configuration')

  @asynccontextmanager
  async def lifecycle(app):
    async with httpx.AsyncClient(timeout=10, trust_env=False, follow_redirects=False,
                                 transport=transport) as client:
      app.state.client = client
      yield

  app = FastAPI(lifespan=lifecycle, docs_url=None, redoc_url=None, openapi_url=None)

  @app.post('/mcp')
  async def forward(request: Request):
    if not hmac.compare_digest(request.headers.get('authorization', '').encode(),
                               ('Bearer ' + access_token).encode()):
      return JSONResponse({'error': 'pilot_access_denied'}, status_code=401)
    if request.url.query or request.headers.get('content-encoding', 'identity') != 'identity':
      return JSONResponse({'error': 'unsupported_pilot_request'}, status_code=400)
    if request.headers.get('content-type', '').split(';')[0] != 'application/json':
      return JSONResponse({'error': 'json_required'}, status_code=415)
    headers = {}
    for raw_name, raw_value in request.scope['headers']:
      name, value = raw_name.decode('latin1').lower(), raw_value.decode('latin1')
      if name in headers:
        return JSONResponse({'error': 'duplicate_header'}, status_code=400)
      headers[name] = value
    connection_tokens = {part.strip().lower() for part in headers.get('connection', '').split(',')}
    if connection_tokens - {'', 'close', 'keep-alive'}:
      return JSONResponse({'error': 'unsupported_connection_tokens'}, status_code=400)
    body = bytearray()
    async for chunk in request.stream():
      body.extend(chunk)
      if len(body) > MAX_BYTES:
        return JSONResponse({'error': 'body_limit_exceeded'}, status_code=413)
    outgoing = {k: v for k, v in headers.items() if k not in TRANSPORT_HEADERS
                and k != 'authorization' and not reserved_header(k)}
    outgoing['host'] = authority
    client = request.app.state.client
    signed = client.build_request('POST', target, headers=outgoing, content=bytes(body))
    message = HttpMessage('POST', authority, '/mcp', dict(signed.headers), bytes(body))
    signed.headers['x-td-attestation'] = sign_attestation(message, {'source_id': 'pilot-adapter'},
                                                       key, nonce=uuid4().hex)
    try:
      async with client.stream('POST', target, headers=signed.headers, content=signed.content) as response:
        if response.headers.get('content-encoding', 'identity') != 'identity':
          return JSONResponse({'error': 'unsupported_response_encoding'}, status_code=502)
        content = bytearray()
        async for chunk in response.aiter_bytes():
          content.extend(chunk)
          if len(content) > MAX_BYTES:
            return JSONResponse({'error': 'response_limit_exceeded'}, status_code=502)
        # Return only protocol-relevant headers. No reserved context or server cookies.
        result_headers = {k: v for k, v in response.headers.items()
                          if k in {'content-type', 'mcp-protocol-version', 'allow'}}
        return Response(bytes(content), status_code=response.status_code, headers=result_headers)
    except httpx.HTTPError:
      return JSONResponse({'error': 'inspection_path_unavailable'}, status_code=502)

  return app


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--proxy', required=True)
  parser.add_argument('--port', type=int, required=True)
  parser.add_argument('--key-file', type=Path, required=True)
  parser.add_argument('--token-file', type=Path, required=True)
  args = parser.parse_args()
  app = create_app(args.proxy, 'pilot.test', args.key_file.read_bytes(), args.token_file.read_text())
  uvicorn.run(app, host='127.0.0.1', port=args.port, access_log=False, log_level='error')
