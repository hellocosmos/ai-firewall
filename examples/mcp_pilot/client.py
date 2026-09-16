"""Official MCP client; deliberately has no signing-key access."""
from contextlib import asynccontextmanager
from datetime import timedelta
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


@asynccontextmanager
async def session(url, token=None):
  headers = {'Authorization': 'Bearer '+token} if token else {}
  async with httpx.AsyncClient(headers=headers, timeout=10, trust_env=False, follow_redirects=False) as http:
    async with streamable_http_client(url, http_client=http, terminate_on_close=False) as streams:
      async with ClientSession(streams[0], streams[1], read_timeout_seconds=timedelta(seconds=12)) as client:
        await client.initialize()
        yield client


def text_content(result):
  return '\n'.join(block.text for block in result.content if block.type == 'text')
