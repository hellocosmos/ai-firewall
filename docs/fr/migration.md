# Migration depuis l’ancien SDK

[English](../en/migration.md) · [한국어](../ko/migration.md) · [简体中文](../zh-CN/migration.md) · [日本語](../ja/migration.md) · [Español](../es/migration.md) · [Français](../fr/migration.md)

L’ancien SDK Python embarqué et son historique restent dans [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security). Ce dépôt est le produit proxy open source. Il n’implique ni compatibilité SDK ni migration automatique des paquets.

1. Recensez les appels HTTP/MCP et les destinations à protéger.
2. Placez un adaptateur de signature fiable après le déchiffrement TLS et imposez le passage par le proxy.
3. Configurez les mappages outil/action explicites, les limites et les champs à masquer.
4. Observez des données synthétiques, puis validez autorisation, masquage, blocage et défaillances inline.
5. Configurez des claims JWT vérifiés et l’Access Broker intégré pour l’accès délégué et l’approbation liée à la requête.

Les utilisateurs du SDK peuvent conserver leur version tout en évaluant un pilote routé séparément. Consultez le [guide de console](console.md). L’installation depuis les sources n’implique ni publication PyPI ni mise à niveau de clients. Sauvegardez l’état avant de changer de version et ne copiez pas les identifiants ou clés synthétiques en production.

## Configuration de 0.38 à 0.39

0.39 rejette volontairement l’ancienne clé `edition`. Utilisez `access_broker_enabled: false` pour un inspector gateway-only et `true` pour le Broker intégré. Le profil auto-hébergé exige `access_broker.enabled`, `access_broker.tenant_id` et les `identity_claims` JWT. Le package et l’image passent de `trapdefense-community` à `trapdefense-ai-firewall`. Sauvegardez le JSON du Broker et l’état de console avant la mise à niveau.
