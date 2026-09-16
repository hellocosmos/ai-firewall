# Community et Enterprise

[English](../en/editions.md) · [한국어](../ko/editions.md) · [简体中文](../zh-CN/editions.md) · [日本語](../ja/editions.md) · [Español](../es/editions.md) · [Français](../fr/editions.md)

Community est le runtime proxy et la console locale sous licence MIT de ce dépôt. Il comprend la vérification du relais signé, les mappages HTTP/MCP explicites, la politique locale, la détection par signatures, le masquage PII, l’inspection bornée des réponses/SSE, l’audit nettoyé, la connexion locale, le changement de mot de passe et les réglages proxy. Aucun paquet privé ni API de modèle externe n’est requis.

Enterprise ajoute Access Broker, distribué séparément : délégation utilisateur/agent/tâche, décisions d’accès et approbation humaine à usage unique, avec expiration et liée à la requête. Le contexte IAM doit provenir d’une intégration de confiance ; la validation avec l’IdP réel du client reste nécessaire. L’interface Community indique les fonctions non incluses.

Le fournisseur privé utilise le point d’entrée Python `trapdefense.authorizers` / `enterprise`. `authorize(request)` applique les décisions ; `evaluate(request)` évalue mirror sans modifier l’état. Sélectionner Enterprise sans fournisseur empêche le démarrage. Les enregistrements de jetons Broker prouvent une décision limitée, ce ne sont pas des jetons OAuth génériques.

La gestion centralisée, la HA distribuée, la facturation hébergée et l’audit immuable ne sont pas livrés. L’offre commerciale peut comprendre fournisseur privé, déploiement, intégration de politiques et support ; tarifs et conditions sont définis séparément. SQLite et JSONL locaux restent modifiables.
