"""Independent credential provider for the configured fixed target."""
from .config import TargetAuth


class CredentialError(ValueError):pass


class TargetCredentialProvider:
  def __init__(self,config: TargetAuth,*,gateway_mode: str,secret: str | None = None):
    self.config,self.gateway_mode,self.secret=config,gateway_mode,secret
    if bool(config.secret_file)!=bool(secret):
      raise ValueError('Configured target secret is unavailable')

  def apply(self,headers: dict[str,str],inbound_authorization: str | None):
    result=dict(headers)
    result.pop('authorization',None)
    if self.config.mode=='passthrough_bearer':
      if inbound_authorization:
        if not inbound_authorization.startswith('Bearer ') or len(inbound_authorization.split(' '))!=2:
          raise CredentialError('unsupported_destination_auth')
        result['authorization']=inbound_authorization
      return result
    if self.gateway_mode=='client_key' and inbound_authorization:
      raise CredentialError('destination_auth_conflict')
    if self.config.mode=='none':return result
    if self.config.mode=='static_bearer':
      result['authorization']='Bearer '+self.secret
      return result
    if self.config.header in result:raise CredentialError('destination_auth_conflict')
    result[self.config.header]=self.config.prefix+self.secret
    return result
