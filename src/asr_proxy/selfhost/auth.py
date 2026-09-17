"""Gateway caller authentication. Tokens and claims never enter audit evidence."""
from dataclasses import dataclass, field
import hmac

import jwt

from .config import ClientKeyGatewayAuth, JwtGatewayAuth, AgentKeyGatewayAuth


class AuthError(ValueError):
  def __init__(self,code: str,status_code: int):
    super().__init__(code)
    self.code,self.status_code=code,status_code


@dataclass(frozen=True)
class GatewayAuthResult:
  subject: str
  scopes: frozenset[str] = frozenset()
  # Only explicitly mapped values are propagated; arbitrary raw claims never leave authentication.
  identity: dict[str, str] = field(default_factory=dict)


class GatewayAuthenticator:
  def __init__(self,config,*,client_key: str,jwk_client=None,agent_credentials=None):
    self.config,self.client_key=config,client_key
    self.agent_credentials=agent_credentials
    self.keys=jwk_client
    if isinstance(config,JwtGatewayAuth) and self.keys is None:
      # Bound unknown-kid refreshes to protect the IdP while accepting normal key rotation quickly.
      self.keys=jwt.PyJWKClient(config.jwks_uri,timeout=5,lifespan=300,cooldown_duration=5)

  def authenticate(self,headers: dict[str,str]):
    if isinstance(self.config,ClientKeyGatewayAuth):
      supplied=headers.get('x-td-client-key','')
      if not hmac.compare_digest(supplied.encode(),self.client_key.encode()):
        raise AuthError('invalid_client_key',401)
      return GatewayAuthResult('client-key')
    if isinstance(self.config,AgentKeyGatewayAuth):
      value=headers.get('authorization','')
      if not value.startswith('Bearer ') or self.agent_credentials is None:
        raise AuthError('invalid_agent_key',401)
      identity=self.agent_credentials.authenticate(value[7:])
      if identity is None:raise AuthError('invalid_agent_key',401)
      approval=headers.get('x-td-approval-id')
      if approval:
        import re
        if not re.fullmatch(r'apv_[a-f0-9]{12}',approval):raise AuthError('invalid_approval_id',400)
        identity['approval_id']=approval
      return GatewayAuthResult(identity['agent_id'],identity=identity)
    value=headers.get('authorization','')
    parts=value.split(' ')
    if len(parts)!=2 or parts[0]!='Bearer' or not parts[1]:
      raise AuthError('invalid_token',401)
    try:
      key=self.keys.get_signing_key_from_jwt(parts[1]).key
      claims=jwt.decode(parts[1],key,algorithms=['RS256'],audience=self.config.audience,
        issuer=self.config.issuer,leeway=30,
        options={'require':['iss','aud','sub','exp','iat']})
      subject=claims['sub']
      if not isinstance(subject,str) or not subject:raise ValueError()
      raw_scopes=claims.get('scope',claims.get('scp',''))
      if isinstance(raw_scopes,str):scopes=frozenset(raw_scopes.split())
      elif isinstance(raw_scopes,list) and all(isinstance(scope,str) for scope in raw_scopes):
        scopes=frozenset(raw_scopes)
      else:raise TypeError()
      if self.config.authorized_parties:
        party=next((claims[name] for name in ('azp','appid','cid') if name in claims),None)
        if not isinstance(party,str) or party not in self.config.authorized_parties:raise ValueError()
    except (jwt.PyJWTError,ValueError,TypeError,KeyError):
      raise AuthError('invalid_token',401) from None
    if not set(self.config.required_scopes).issubset(scopes):
      raise AuthError('insufficient_scope',403)
    identity = {}
    mapping = self.config.identity_claims
    if mapping is not None:
      required = ('tenant_id','agent_id') if self.config.identity_mode=='agent' else ('tenant_id','user_id','agent_id','delegation_id','task_id')
      for field_name, claim_name in mapping.model_dump().items():
        if self.config.identity_mode=='agent' and field_name in ('user_id','task_id','delegation_id'):
          continue
        if claim_name is None:
          continue
        value = claims.get(claim_name)
        if value is None and field_name not in required:
          continue
        if not isinstance(value,str) or not value or len(value)>256:
          raise AuthError('invalid_agent_identity',401)
        identity[field_name]=value
      if self.config.identity_mode=='agent':identity['authorization_mode']='agent'
    return GatewayAuthResult(subject,scopes,identity)

  def metadata(self):
    if not isinstance(self.config,JwtGatewayAuth):return None
    return {'resource':self.config.resource,
      'authorization_servers':self.config.authorization_servers,
      'bearer_methods_supported':['header'],'scopes_supported':self.config.required_scopes}

  def challenge(self,error: AuthError | None = None):
    if not isinstance(self.config,JwtGatewayAuth):return None
    value=f'Bearer resource_metadata="{self.config.metadata_url}"'
    if error:
      value+=f', error="{error.code}"'
      if error.code=='insufficient_scope':
        value+=f', scope="{" ".join(self.config.required_scopes)}"'
    return value
