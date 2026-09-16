# Compatibilité des clients de passerelle — 0.37

[English](../en/gateway-compatibility.md) · [한국어](../ko/gateway-compatibility.md) · [简体中文](../zh-CN/gateway-compatibility.md) · [日本語](../ja/gateway-compatibility.md) · [Español](../es/gateway-compatibility.md) · [Français](../fr/gateway-compatibility.md)

Le client doit pouvoir remplacer l’URL HTTP/MCP distante par TrapDefense et utiliser un en-tête de clé de connexion ou un JWT Bearer OAuth. L’authentification client→TrapDefense est séparée de l’authentification TrapDefense→cible.

| Chemin | Preuve 0.37 |
|---|---|
| JSON HTTP générique | Intégration synthétique vérifiée avec HTTPX |
| SDK Python MCP officiel 1.30.0 | Le SDK réel a effectué initialisation, notification et liste d’outils en Streamable HTTP vers une cible synthétique |
| MCP distant VS Code | Configuration compatible avec `url`, `headers` et OAuth officiels ; exécution dans VS Code non vérifiée |
| Métadonnées OAuth et JWT RS256 | Lecture HTTP réelle de JWKS et validation synthétique de issuer/audience/time/subject/scope |
| Entra/Okta/Keycloak réel | Validation séparée du tenant, TLS, Conditional Access et révocation requise |
| MCP avec état, SSE longue durée, WebSocket, stdio | Non pris en charge par ce profil |

`gateway_auth` utilise `client_key` ou `jwt`. En mode JWT, TrapDefense agit comme OAuth Resource Server et publie les métadonnées RFC 9728 ainsi que le défi `WWW-Authenticate`. La connexion, l’émission, DCR, refresh et OBO appartiennent à l’IdP externe ou à un fournisseur d’identifiants séparé.

`target_auth` prend en charge `none`, `passthrough_bearer`, `static_bearer` et `static_api_key`. Le JWT de passerelle n’est pas transmis à la cible. `passthrough_bearer` sert uniquement à l’intégration HTTP héritée avec client-key et ne constitue pas une conformité OAuth MCP.

Avant d’approuver une intégration, vérifiez URL, deux authentifications, initialisation/découverte MCP, action autorisée et refusée, effet côté cible, PII/secret, 401 cible, panne d’inspection et absence de fallback direct. La configuration et l’exemple VS Code figurent dans le [guide anglais](../en/gateway-compatibility.md).
