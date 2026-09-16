# Community et Enterprise

[English](../en/editions.md) · [한국어](../ko/editions.md) · [简体中文](../zh-CN/editions.md) · [日本語](../ja/editions.md) · [Español](../es/editions.md) · [Français](../fr/editions.md)

## Compatibilité et disponibilité

0.36 fournit un paquet Docker Compose en préversion : adaptateur, Envoy, inspecteur et console. L’image se construit localement depuis les sources. TrapDefense Cloud reste prévu, sans inscription disponible.

[Offres et compatibilité](deployment-fit.md)

Community inclut le SSO de console Microsoft Entra ID à locataire unique, avec les rôles Administrateur et Lecteur. L’authentification de console n’autorise pas les actions des agents ; délégation et approbation restent dans Enterprise. [Entra SSO](identity.md).

## État actuel de livraison

| Périmètre | État | Preuve et limite |
|---|---|---|
| Runtime et console Community | **Community Preview public** | Publié dans ce dépôt MIT ; CI et vérification synthétique du trajet Envoy réussissent. Trafic et capacité de production exigent une validation client. |
| Enterprise Access Broker | **Implémentation pilote privée** | Le fournisseur et le flux d’approbation distribués séparément existent ; ils ne figurent pas dans ce dépôt et ne sont pas présentés comme disponibles à tous. IAM réel, politique client et pannes doivent être validés. |
| Fleet central, HA distribuée, audit immuable et service hébergé | **Feuille de route** | Non livrés et non représentés comme fonctionnalités par les écrans Community. |

Les noms d’édition définissent les limites de produit et de licence, sans affirmer que toute la feuille de route Enterprise est disponible à tous.

Community est le runtime proxy et la console locale sous licence MIT de ce dépôt. Il comprend la vérification du relais signé, les mappages HTTP/MCP explicites, la politique locale, la détection par signatures, le masquage PII, l’inspection bornée des réponses/SSE, l’audit nettoyé, la connexion locale, le changement de mot de passe et les réglages proxy. Aucun paquet privé ni API de modèle externe n’est requis.

L’implémentation pilote Enterprise distribuée séparément ajoute Access Broker : délégation utilisateur/agent/tâche, décisions d’accès et approbation humaine à usage unique, avec expiration et liée à la requête. Le contexte IAM doit provenir d’une intégration de confiance ; la validation avec l’IdP réel du client reste nécessaire. L’interface Community indique les fonctions non incluses.

Le fournisseur privé utilise le point d’entrée Python `trapdefense.authorizers` / `enterprise`. `authorize(request)` applique les décisions ; `evaluate(request)` évalue mirror sans modifier l’état. Sélectionner Enterprise sans fournisseur empêche le démarrage. Les enregistrements de jetons Broker prouvent une décision limitée, ce ne sont pas des jetons OAuth génériques.

La gestion centralisée, la HA distribuée, la facturation hébergée et l’audit immuable ne sont pas livrés. L’offre commerciale peut comprendre fournisseur privé, déploiement, intégration de politiques et support ; tarifs et conditions sont définis séparément. SQLite et JSONL locaux restent modifiables.

[Docker 0.36](self-hosting.md)
