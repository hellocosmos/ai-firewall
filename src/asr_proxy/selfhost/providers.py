"""Native provider profiles; exact destinations and model allowlists, never an open proxy."""
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

ORIGINS = {'openai':'https://api.openai.com', 'anthropic':'https://api.anthropic.com',
  'google':'https://generativelanguage.googleapis.com', 'openrouter':'https://openrouter.ai'}
SDK_HEADERS = ('authorization','x-api-key','x-goog-api-key','x-td-client-key')


class ProviderProfile(BaseModel):
  model_config = ConfigDict(extra='forbid')
  provider: Literal['openai','anthropic','google','openrouter']
  models: list[str] = Field(min_length=1,max_length=20)
  timeout_seconds: int = Field(default=120,ge=10,le=300)

  @model_validator(mode='after')
  def validate_models(self):
    if len(set(self.models)) != len(self.models) or any(
        not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]{0,127}',model)
        or '..' in model or '//' in model for model in self.models):
      raise ValueError('Configure unique explicit model identifiers')
    if self.provider=='google' and any('/' in model for model in self.models):
      raise ValueError('Gemini models use bare model names')
    return self

  def routes(self):
    authority=ORIGINS[self.provider].split('://')[1]
    def route(path,tool,fields,resource=None):
      return dict(authority=authority,path=path,protocol='http',tool=tool,
        llm_provider=self.provider,allowed_models=self.models,
        rule={'action':'invoke','effect':'allow',**({'resource':resource} if resource else {'resource_pointer':'/model'})},
        redact_fields=fields)
    chat=['/messages/*/content','/messages/*/content/*/text',
      '/messages/*/tool_calls/*/function/arguments','/messages/*/function_call/arguments']
    if self.provider=='openai':
      return [route('/v1/chat/completions','llm.chat',chat),
        route('/v1/responses','llm.responses',['/input','/instructions','/input/*/content','/input/*/content/*/text',
          '/input/*/arguments','/input/*/output'])]
    if self.provider=='anthropic':
      return [route('/v1/messages','llm.messages',['/system','/system/*/text','/messages/*/content',
        '/messages/*/content/*/text','/messages/*/content/*/content','/messages/*/content/*/content/*/text'])]
    if self.provider=='openrouter':return [route('/api/v1/chat/completions','llm.chat',chat)]
    result=[route('/v1beta/openai/chat/completions','llm.chat',chat)]
    for model in self.models:
      for method in ('generateContent','streamGenerateContent'):
        result.append(route(f'/v1beta/models/{model}:{method}','llm.generate',
          ['/contents/*/parts/*/text','/systemInstruction/parts/*/text'],resource=model))
    return result

  def target(self):
    if self.provider in ('anthropic','google'):
      return {'mode':'static_api_key','secret_file':'/run/secrets/provider-key',
        'header':'x-api-key' if self.provider=='anthropic' else 'x-goog-api-key'}
    return {'mode':'static_bearer','secret_file':'/run/secrets/provider-key'}


def gateway_headers(headers, profile, mode):
  """Interpret the SDK api_key as gateway admission, then discard all credential slots."""
  values=[(key,headers[key]) for key in SDK_HEADERS if headers.get(key)]
  if len(values)!=1:raise ValueError('ambiguous_gateway_credentials')
  name,credential=values[0]
  allowed={'authorization','x-td-client-key'}
  if profile.provider=='anthropic':allowed.add('x-api-key')
  if profile.provider=='google':allowed.add('x-goog-api-key')
  if name not in allowed:raise ValueError('unsupported_gateway_credential_header')
  if name=='authorization':
    if not credential.startswith('Bearer ') or len(credential.split())!=2:
      raise ValueError('invalid_gateway_credential')
    credential=credential[7:]
  clean={k:v for k,v in headers.items() if k not in SDK_HEADERS}
  auth=dict(clean)
  auth['x-td-client-key' if mode=='client_key' else 'authorization']=credential if mode=='client_key' else 'Bearer '+credential
  return clean,auth
