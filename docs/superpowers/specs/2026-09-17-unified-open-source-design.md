# Unified Open Source Product Design

**Date:** 2026-09-17  
**Release:** 0.39  
**Status:** Approved for implementation

## Goal

Ship TrapDefense as one MIT-licensed AI Firewall for Agents. The public repository must run the Runtime Gateway, content inspection, Agent Registry, delegation, Access Broker, human approval, audit, self-hosted gateway, and operator console without a private runtime package.

## Product boundary

The open-source product contains all enforcement code and local operations needed for a single deployment. Future commercial work may provide a managed cloud service, fleet operations, multi-node HA, immutable external audit storage, customer-specific integrations, and support. Those services do not remove features from the open-source runtime.

Internal strategy, customer material, credentials, and deployment secrets remain outside the public repository.

## Runtime architecture

1. A caller authenticates to the self-hosted gateway with a client key or a standards-based JWT.
2. The gateway maps the verified JWT claims to a normalized agent identity when the Access Broker is enabled.
3. The trusted adapter signs the normalized identity and exact request digest for the inspector.
4. The inspector validates the trusted hop, inspects HTTP or MCP content, applies PII and secret policy, and evaluates local route policy.
5. When enabled, the built-in Access Broker evaluates agent registration, delegation, task, resource, action, and optional one-time approval.
6. The gateway forwards only an allowed or safely redacted request to its configured destination and inspects the response before returning it.

Runtime Gateway and Access Broker remain separate security boundaries. A trusted-hop signature proves the adapter and request binding; it does not create agent identity. Agent identity comes from verified JWT claims or from the explicitly labeled synthetic demo.

## Configuration

The `edition` switch and private `trapdefense.authorizers` entry point are removed. `InspectionConfig.access_broker_enabled` selects local policy only or local policy plus the built-in broker.

Self-hosted deployments enable broker identity with an explicit JWT claim map. Broker startup fails closed when identity mapping is incomplete or when a non-JWT gateway mode is selected. Client-key authentication remains valid for gateway-only deployments and does not make an identity-verified claim.

## Operator console

The local demo seeds a synthetic tenant, agent, and delegation in the real built-in broker store. Operators can register agents, create delegations, review approvals, approve or deny a bound action, and replay the action with the approval. The UI labels synthetic evidence and Access Broker maturity explicitly.

Self-hosted mode exposes the same broker UI only when the broker is enabled in deployment configuration.

## Compatibility and migration

Version 0.39 is a pre-1.0 configuration break:

- remove `edition: community|enterprise`;
- replace it with `access_broker_enabled: true|false`;
- remove the private provider package and entry-point requirement;
- rename the Python distribution and container image from `trapdefense-community` to `trapdefense-ai-firewall`;
- keep the existing CLI commands and HTTP/MCP protocol behavior.

Old edition configuration is rejected instead of silently changing the authorization boundary.

## Evidence and limitations

Unit, integration, synthetic OIDC, Docker, and browser tests establish source and protocol behavior. They do not prove a production Entra, Okta, or Keycloak tenant; customer-specific MCP authentication; multi-node HA; production TLS; or Conditional Access behavior. The Access Broker is therefore labeled **Experimental** in 0.39.

## Acceptance criteria

- A clean install from the public repository requires no private distribution.
- Gateway-only and broker-enabled modes both fail closed at their stated boundary.
- A broker-enabled request can be allowed, blocked, require approval, and consume exactly one matching approval.
- The console demonstrates the real broker path with synthetic identities.
- Public documentation is English-first with Korean, Chinese, Japanese, Spanish, and French navigation/content maintained.
- Repository tests, console build, Docker smoke tests, secret scan, and landing-page visual checks pass.
- GitHub and trapdefense.com describe one open-source product and distinguish implemented, experimental, and planned capabilities.
