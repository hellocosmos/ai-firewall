"""Construct the optional built-in Agent Access Broker."""

from asr_proxy.access_broker import AccessBroker, AccessRequest, FileAccessBrokerStore

from .contracts import InspectionConfig

AuthorizationRequest = AccessRequest


def load_authorizer(config: InspectionConfig):
  if not config.access_broker_enabled:
    return None
  return AccessBroker(FileAccessBrokerStore(config.broker_store))
