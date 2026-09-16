# Community and Enterprise

| Capability | Community (MIT, this repository) | Enterprise (separate private package) |
|---|---|---|
| Post-decryption HTTP/MCP proxy inspection | Included | Uses the same inspection boundary |
| Local allow/block mappings and egress policy | Included | Included |
| Signature checks and PII handling | Included | Included |
| Signed trusted-hop source and replay checks | Included | Included |
| Buffered response/SSE inspection | Included, bounded | Included, bounded |
| Sanitized local audit evidence | Included | Extended with access-decision context |
| User/agent/task delegation decisions | Not included | Implemented in the Access Broker |
| Request-bound human approval | Not included | Implemented; one-time, expiring approval |
| Existing IAM context integration | No user/agent identity claim | Integration path; real customer IdP validation remains required |
| Central fleet policy, HA, managed service, immutable audit | Not included | Roadmap, not shipped claims |

Enterprise extends the same proxy through the `trapdefense.authorizers` / `enterprise` Python entry point. The provider exposes `authorize(request)` and `evaluate(request)`; the latter is non-mutating for mirror assessment. The public request schema is in `inspection/authorization.py`. The private implementation is not part of the MIT package.

An approval controls the specific observed request; it is not blanket future permission. Broker token records are scoped decision evidence, not independently verifiable OAuth access tokens for arbitrary downstream services. Deployment and identity-provider integration must establish that downstream trust separately.

Commercial offerings: private authorization features, deployment and policy integration, and support. Pricing and production support terms are agreed separately. This repository does not implement license enforcement, billing or a hosted service.
