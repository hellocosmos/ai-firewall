"""Bounded authenticated adapter. Never retries or bypasses Envoy."""
import asyncio
import hmac
from uuid import uuid4
from urllib.parse import urlsplit
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from asr_proxy.inspection.contracts import HttpMessage, InspectionError
from asr_proxy.inspection.identity import sign_attestation, reserved_header, TRANSPORT_HEADERS
from asr_proxy.inspection.server import bounded_body


def create_gateway(config, client_key, signing_key, *, bearer=None, transport=None):
  app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
  authority = urlsplit(config.upstream).netloc
  slots = asyncio.Semaphore(32)

  @app.api_route('/{path:path}', methods=['GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS','CONNECT'])
  async def forward(request: Request):
    # Do not echo submitted values, URLs, credentials or transport exception details.
    headers = {}
    for key, value in request.scope['headers']:
      name = key.decode('latin1').lower()
      if name in headers: return JSONResponse({'error':'duplicate_header'}, status_code=400)
      headers[name] = value.decode('latin1')
    supplied = headers.get('x-td-client-key', '')
    if not hmac.compare_digest(supplied.encode(), client_key.encode()):
      return JSONResponse({'error':'invalid_client_key'}, status_code=401)
    if slots.locked(): return JSONResponse({'error':'gateway_busy'}, status_code=503)
    raw_path = request.scope.get('raw_path', b'/').decode('ascii')
    if (request.method, raw_path) not in {(r.method,r.path) for r in config.routes}:
      return JSONResponse({'error':'unmapped_route'}, status_code=403)
    if any(name in headers for name in ('upgrade','cookie','mcp-session-id','proxy-authorization')):
      return JSONResponse({'error':'unsupported_session_or_upgrade'}, status_code=400)
    if headers.get('content-encoding','identity').lower() != 'identity':
      return JSONResponse({'error':'unsupported_content_encoding'}, status_code=415)
    if 'authorization' in headers and not headers['authorization'].startswith('Bearer '):
      return JSONResponse({'error':'unsupported_destination_auth'},status_code=400)
    if bearer and 'authorization' in headers:
      return JSONResponse({'error':'destination_auth_conflict'}, status_code=400)
    try:
      async with slots, asyncio.timeout(12):
        body = await bounded_body(request, config.max_body_bytes)
        if body and headers.get('content-type','').split(';')[0].strip() not in ('application/json','application/json-rpc'):
          return JSONResponse({'error':'unsupported_request_media_type'},status_code=415)
        clean = {k:v for k,v in headers.items() if k not in TRANSPORT_HEADERS and not reserved_header(k)}
        # Reject connection-nominated application headers rather than silently changing semantics.
        nominated = {s.strip().lower() for s in headers.get('connection','').split(',')}
        if nominated - {'','close','keep-alive'}:
          return JSONResponse({'error':'unsupported_connection_header'}, status_code=400)
        clean['host'] = authority
        clean['accept-encoding'] = 'identity'
        if bearer: clean['authorization'] = 'Bearer ' + bearer
        query = request.scope.get('query_string', b'')
        target = raw_path + ('?' + query.decode('ascii') if query else '')
        async with httpx.AsyncClient(timeout=8, trust_env=False, follow_redirects=False, transport=transport) as client:
          outgoing = client.build_request(request.method, 'http://envoy:18082'+target, headers=clean, content=body)
          # Sign the actual serialized target and defaults added by the HTTP client.
          message = HttpMessage(request.method, authority, outgoing.url.raw_path.decode('ascii'), dict(outgoing.headers), body)
          outgoing.headers['x-td-attestation'] = sign_attestation(message,
            {'source_id':'selfhost-adapter','run_id':uuid4().hex}, signing_key, nonce=uuid4().hex)
          response = await client.send(outgoing, stream=True)
          try:
            if 300 <= response.status_code < 400:
              return JSONResponse({'error':'upstream_redirect_not_supported'}, status_code=502)
            if response.headers.get('content-type','').split(';')[0] == 'text/event-stream':
              return JSONResponse({'error':'streaming_not_supported'}, status_code=502)
            if 'set-cookie' in response.headers or 'mcp-session-id' in response.headers:
              return JSONResponse({'error':'upstream_session_not_supported'}, status_code=502)
            data = bytearray()
            async for chunk in response.aiter_raw():
              if len(data)+len(chunk)>config.max_body_bytes:
                return JSONResponse({'error':'response_limit_exceeded'}, status_code=502)
              data.extend(chunk)
            output = {k:v for k,v in response.headers.items() if k not in TRANSPORT_HEADERS and not reserved_header(k)
                      and k not in ('server','www-authenticate')}
            return Response(bytes(data),status_code=response.status_code,headers=output)
          finally: await response.aclose()
    except InspectionError:
      return JSONResponse({'error':'request_limit_exceeded'}, status_code=413)
    except (httpx.HTTPError, TimeoutError):
      return JSONResponse({'error':'inspection_path_unavailable'}, status_code=503)
  return app
