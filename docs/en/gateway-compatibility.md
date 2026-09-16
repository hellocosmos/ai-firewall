# Gateway client compatibility — 0.37

[English](../en/gateway-compatibility.md) · [한국어](../ko/gateway-compatibility.md) · [简体中文](../zh-CN/gateway-compatibility.md) · [日本語](../ja/gateway-compatibility.md) · [Español](../es/gateway-compatibility.md) · [Français](../fr/gateway-compatibility.md)

TrapDefense uses a normal remote HTTP/MCP endpoint. A client must let you replace the destination URL and use either a configured header or an OAuth Bearer token. Authentication from the client to TrapDefense is separate from authentication from TrapDefense to the target.

```text
Client -- gateway credential --> TrapDefense -- target credential --> MCP / API
```

## Evidence matrix

| Client or flow | 0.37 status | Evidence and limit |
|---|---|---|
| Generic JSON HTTP client | **Synthetic integration verified** | HTTPX sends allowed and denied requests through the FastAPI adapter and fixed Envoy hop. |
| Official Python MCP SDK 1.30.0 | **Synthetic integration verified** | The real SDK completes Streamable HTTP `initialize`, `notifications/initialized`, and `tools/list` through the gateway against a synthetic target. |
| VS Code remote MCP | **Configuration compatible; product execution not yet verified** | Current official configuration supports HTTP `url`, `headers`, secret inputs, and OAuth. The example below has been source-checked, not run inside VS Code. |
| OAuth Protected Resource Metadata and RS256 JWT | **Protocol-realistic synthetic verification** | Ephemeral RSA signing, actual HTTP JWKS retrieval, issuer, audience, time, subject, and scope validation pass locally. This is not evidence from a real Entra tenant. |
| Real Entra/Okta/Keycloak tenant, Conditional Access, revocation | **Deployment validation required** | Provider registration, claims, policy, TLS, and client behavior remain environment-specific. |
| Stateful MCP, long-lived SSE, WebSocket, stdio | **Unsupported by this profile** | 0.37 remains bounded stateless JSON over HTTP. |

## VS Code with a connection key

Use an input variable instead of committing a key to `.vscode/mcp.json`:

```json
{
  "inputs": [
    {
      "type": "promptString",
      "id": "trapdefense-key",
      "description": "TrapDefense connection key",
      "password": true
    }
  ],
  "servers": {
    "trapDefense": {
      "type": "http",
      "url": "https://firewall.example.com/mcp",
      "headers": {
        "X-TD-Client-Key": "${input:trapdefense-key}"
      }
    }
  }
}
```

VS Code first tries Streamable HTTP for an HTTP MCP server. TrapDefense 0.37 verifies the protocol with the official Python SDK; run the acceptance checklist with your exact VS Code version before declaring support.

## JWT resource-server mode

```yaml
gateway_auth:
  mode: jwt
  issuer: https://login.example.com/tenant/v2.0
  audience: https://firewall.example.com/mcp
  jwks_uri: https://login.example.com/tenant/discovery/v2.0/keys
  resource: https://firewall.example.com/mcp
  authorization_servers:
    - https://login.example.com/tenant/v2.0
  required_scopes: [mcp.invoke]

target_auth:
  mode: static_bearer
  secret_file: /run/secrets/target-token
```

The client sends a JWT issued for the TrapDefense resource. TrapDefense validates it and consumes it. The configured target receives the separate target token. The gateway JWT is never used as the target credential.

For MCP, a missing or invalid token returns `401` plus a gateway-owned `WWW-Authenticate` header pointing to RFC 9728 metadata. A valid token without every required scope returns `403`. TrapDefense publishes metadata but does not provide authorization, token, callback, registration, refresh, or logout endpoints; the configured external authorization server owns those functions.

## Target credential modes

| Mode | Behavior |
|---|---|
| `none` | Sends no target credential. A client-key caller that submits `Authorization` is rejected rather than silently stripped. |
| `passthrough_bearer` | For legacy HTTP onboarding with `client_key` mode only. The caller's Bearer token reaches the fixed target. Do not describe this as MCP OAuth compliance. |
| `static_bearer` | Injects `Authorization: Bearer` from an owner-only file. A caller-supplied Authorization header is rejected. |
| `static_api_key` | Injects a file-backed value into a configured non-reserved header such as `X-API-Key` or `Ocp-Apim-Subscription-Key`. |

## Acceptance checklist

Verify the exact client and service combination: endpoint replacement; gateway authentication; target authentication; MCP initialize/discovery if applicable; one allowed action; one denied action without target side effect; PII/secret handling; target `401`; inspection-path outage; and no direct-URL fallback. Inspect target logs and TrapDefense's sanitized evidence. Container health alone is insufficient.

## Standards and vendor references

- [MCP Authorization Specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)
- [VS Code MCP configuration](https://code.visualstudio.com/docs/agents/reference/mcp-configuration)
- [Azure API Management MCP security](https://learn.microsoft.com/en-us/azure/api-management/secure-mcp-servers)
- [Amazon Bedrock AgentCore gateway authorization](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-building-adding-targets-authorization.html)
