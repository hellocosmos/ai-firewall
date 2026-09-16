# Migration depuis l’ancien SDK

[English](../en/migration.md) · [한국어](../ko/migration.md) · [简体中文](../zh-CN/migration.md) · [日本語](../ja/migration.md) · [Español](../es/migration.md) · [Français](../fr/migration.md)

L’ancien SDK Python embarqué et son historique restent dans [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security). Ce dépôt est le nouveau produit proxy Community. Il n’implique ni compatibilité SDK ni migration automatique des paquets.

1. Recensez les appels HTTP/MCP et les destinations à protéger.
2. Placez un adaptateur de signature fiable après le déchiffrement TLS et imposez le passage par le proxy.
3. Configurez les mappages outil/action explicites, les limites et les champs à masquer.
4. Observez des données synthétiques, puis validez autorisation, masquage, blocage et défaillances inline.
5. Ajoutez le fournisseur privé Enterprise si vous avez besoin d’accès délégué et d’approbation liée à la requête.

Les utilisateurs du SDK peuvent conserver leur version tout en évaluant un pilote routé séparément. Consultez le [guide de console](console.md). L’installation depuis les sources n’implique ni publication PyPI ni mise à niveau de clients. Sauvegardez l’état avant de changer de version et ne copiez pas les identifiants ou clés synthétiques en production.
