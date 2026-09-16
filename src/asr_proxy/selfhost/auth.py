"""Gateway caller authentication. Tokens and claims never enter audit evidence."""
from dataclasses import dataclass, field
import hmac

import jwt

from .config import ClientKeyGatewayAuth, JwtGatewayAuth


class AuthError(ValueError):
  def __init__(self,code: str,status_code: int):
    super().__init__(code)
    self.code,self.status_code=code,status_code


@dataclass(frozen=True)
class GatewayAuthResult:
  subject: str
  scopes: frozenset[str] = frozenset()
  # Deliberately empty: raw claims are not propagated into inspection or audit.
  claims: dict = field(default_factory=dict)


class GatewayAuthenticator:
  def __init__(self,config,*,client_key: str,jwk_client=None):
    self.config,self.client_key=config,client_key
    self.keys=jwk_client
    if isinstance(config,JwtGatewayAuth) and self.keys is None:
      self.keys=jwt.PyJWKClient(config.jwks_uri,timeout=5,lifespan=300)

  def authenticate(self,headers: dict[str,str]):
    if isinstance(self.config,ClientKeyGatewayAuth):
      supplied=headers.get('x-td-client-key','')
      if not hmac.compare_digest(supplied.encode(),self.client_key.encode()):
        raise AuthError('invalid_client_key',401)
      return GatewayAuthResult('client-key')
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
      if not isinstance(raw_scopes,str):raise TypeError()
      scopes=frozenset(raw_scopes.split())
    except (jwt.PyJWTError,ValueError,TypeError,KeyError):
      raise AuthError('invalid_token',401) from None
    if not set(self.config.required_scopes).issubset(scopes):
      raise AuthError('insufficient_scope',403)
    return GatewayAuthResult(subject,scopes)

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

