# Compatibilité et disponibilité

[English](../en/deployment-fit.md) · [한국어](../ko/deployment-fit.md) · [简体中文](../zh-CN/deployment-fit.md) · [日本語](../ja/deployment-fit.md) · [Español](../es/deployment-fit.md) · [Français](../fr/deployment-fit.md)

Protégez les appels HTTP API et MCP distants que vous pouvez acheminer via un chemin d’inspection pris en charge. Conservez l’authentification des serveurs MCP et connecteurs ; ne remplacez pas votre IAM.

0.38 fournit un paquet Docker Compose avec clé ou JWT externe pour la passerelle et identifiants indépendants pour la cible. L’image se construit depuis les sources ; TrapDefense Cloud reste prévu.

Vous devez contrôler l’adresse du client, l’entrée du serveur ou un chemin d’inspection réseau compatible. Le service cible doit être joignable et le contournement empêché. Les appels internes SaaS, stdio local, shell, fichiers et accès directs aux bases de données sont hors périmètre du proxy HTTP.

Le pilote local 0.35 vérifie Streamable HTTP sans état avec réponses JSON. L’inspection SSE limitée ne certifie pas tous les serveurs MCP en streaming. OAuth, sessions avec état et identité client exigent une validation. Le SSO Entra de la console n’est ni un IAM d’agents ni une autorisation du service cible.

[Architecture](architecture.md) · [Delivery status](editions.md) · [MCP pilot](mcp-pilot.md)

[Auto-hébergement Docker](self-hosting.md) · [Compatibilité de la passerelle](gateway-compatibility.md)
