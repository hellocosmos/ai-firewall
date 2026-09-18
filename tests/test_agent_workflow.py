"""Agent loop rejects unsafe destinations and malformed/repeated tool proposals."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
import pytest
pytest.importorskip('openai')
pytest.importorskip('mcp')
from examples.agent_workflow.agent import checked_call,gateway_url
from jsonschema import ValidationError


def call(name='notes_read',arguments='{"message":"customer"}'):
  return SimpleNamespace(id='call_1',function=SimpleNamespace(name=name,arguments=arguments))


def test_tool_proposals_are_bounded_by_discovery():
  schemas={'notes_read':{'type':'object','properties':{'message':{'type':'string'}},'required':['message'],'additionalProperties':False}}
  seen=set()
  assert checked_call(call(),schemas,seen)==('notes_read',{'message':'customer'})
  with pytest.raises(ValueError,match='repeated'):checked_call(call(),schemas,seen)
  with pytest.raises(ValueError):checked_call(call('unknown'),schemas,set())
  with pytest.raises(ValidationError):checked_call(call(arguments='{"message":7}'),schemas,set())
  with pytest.raises(ValueError):checked_call(call(arguments='[]'),schemas,set())


@pytest.mark.parametrize('url',['https://api.openai.com/v1','http://evil.test/v1',
  'http://secret@127.0.0.1:80/v1','http://127.0.0.1:80/v1?key=x'])
def test_no_direct_or_credential_urls(url):
  with pytest.raises(ValueError):gateway_url(url)


@pytest.mark.asyncio
@pytest.mark.parametrize('behavior,expected',[('no_calls','no_tool_call'),('unknown','invalid_tool_call'),('repeat','invalid_tool_call'),('valid','finished')])
async def test_agent_loop_requires_actual_valid_tool_calls(monkeypatch,behavior,expected):
  from contextlib import asynccontextmanager
  from examples.agent_workflow import agent
  class ToolCall:
    id='call_1'
    function=SimpleNamespace(name='unknown' if behavior=='unknown' else 'notes_read',arguments='{"message":"customer"}')
    def model_dump(self,**kwargs):
      return {'id':self.id,'type':'function','function':vars(self.function)}
  invoked=[]
  class MCP:
    async def list_tools(self):return SimpleNamespace(tools=[SimpleNamespace(name='notes_read',description='Read',inputSchema={'type':'object'})])
    async def call_tool(self,name,args):
      invoked.append(name)
      return SimpleNamespace(isError=False,content=[SimpleNamespace(type='text',text='[REDACTED]')])
  @asynccontextmanager
  async def mock_session(*args):yield MCP()
  class SDK:
    def __init__(self,**kwargs):self.turn=0;self.chat=SimpleNamespace(completions=self)
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    async def create(self,**kwargs):
      self.turn+=1
      calls=[] if behavior=='no_calls' or (behavior=='valid' and self.turn==2) else [ToolCall()]
      return SimpleNamespace(choices=[SimpleNamespace(finish_reason='tool_calls' if calls else 'stop',message=SimpleNamespace(tool_calls=calls,content='done'))])
  monkeypatch.setattr(agent,'session',mock_session);monkeypatch.setattr(agent,'AsyncOpenAI',SDK)
  result=await agent.run('http://127.0.0.1:10001/v1','test','synthetic','http://127.0.0.1:10002/mcp','test')
  assert result['status']==expected
  assert len(invoked)==(1 if behavior in ('valid','repeat') else 0)
