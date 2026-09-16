# TrapDefense — AI Firewall pour les agents

[English](README.md) · [한국어](README.ko.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md)

> **Community Preview :** adapté à l’évaluation locale et à l’intégration. Le trafic de production, la HA, la capacité et les chemins d’identité client nécessitent une validation distincte.

**Contrôlez tout le chemin du prompt à l’action.**

TrapDefense Community est un AI Firewall auto-hébergé avec console locale. Inspectez les appels HTTP et MCP pris en charge, appliquez les politiques d’action, masquez les données sensibles et conservez les preuves des décisions. L’ancien SDK reste dans [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security).

```text
AI agents → TrapDefense AI Firewall → Tools / MCP servers / APIs
            Action policy · Data protection · Audit
          ← Inspected responses ←
```

Flux logique du produit. Consultez l’[architecture de déploiement](docs/fr/architecture.md) pour les exigences de transfert de confiance, de visibilité du trafic et de routage.

Community inclut le SSO de console Microsoft Entra ID à locataire unique, avec les rôles Administrateur et Lecteur. L’authentification de console n’autorise pas les actions des agents ; délégation et approbation restent dans Enterprise. [Entra SSO](docs/fr/identity.md).

## Compatibilité et disponibilité

Protégez les appels HTTP API et MCP distants que vous pouvez acheminer via un chemin d’inspection pris en charge. Conservez l’authentification des serveurs MCP et connecteurs ; ne remplacez pas votre IAM.

Self-hosted Community est une préversion installée depuis les sources avec des exemples de proxy Docker. Un paquet Docker intégré est prévu. TrapDefense Cloud est également prévu, avec le même socle d’inspection ; aucune inscription ni utilisation n’est encore disponible.

[Offres et compatibilité](docs/fr/deployment-fit.md)

## Pourquoi TrapDefense

TrapDefense gouverne le point où la sortie du modèle devient une action réelle. Il réunit un point d’application par proxy, une protection locale des données et des limites d’identité explicites.

| Limite | Ce que TrapDefense rend explicite |
|---|---|
| **Point d’application indépendant** | Les appels HTTP et MCP pris en charge traversent Envoy et l’inspecteur avant d’atteindre la destination configurée. L’application n’intègre pas l’ancien SDK. Le déploiement doit empêcher les chemins de contournement. |
| **Contrôle bidirectionnel des données** | Les requêtes et réponses complètes et bornées, y compris SSE pris en charge, peuvent être autorisées, bloquées ou masquées par les politiques d’action, de PII et de secrets. |
| **Limite d’identité explicite** | Le SSO Entra ID de Community authentifie l’opérateur de console. Le pilote Enterprise séparé évalue utilisateur, agent, délégation, tâche, ressource et action. |
| **Sémantique de panne claire** | Inline bloque en cas d’échec d’inspection. Mirror enregistre les résultats hypothétiques `would_*` sans modifier le trafic d’origine ni l’état d’approbation. |
| **Preuves exploitables** | La console locale présente décisions, couverture des politiques, reçus de destination et preuves nettoyées sans copier le contenu protégé dans l’audit. |

## Évaluation locale en cinq minutes

Prérequis : Python 3.11+, Node.js 22.12+ ou 24, npm et Docker Engine/Desktop local. Installation depuis les sources ; aucune publication PyPI n’est impliquée.

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall
./scripts/install-console.sh
./scripts/run-console.sh
```

Ouvrez [http://127.0.0.1:5176](http://127.0.0.1:5176). Connectez-vous avec `admin` / `1234`, puis changez le mot de passe dans les paramètres. L’anglais est la langue par défaut. Le sélecteur fonctionne avant et après connexion ; le navigateur mémorise votre choix.

Le résultat attendu affiche proxy, inspecteur et destination prêts dans **Connexions / Système** ; **Lire les notes métier** doit produire HTTP 200 et un reçu de destination. Le mot de passe initial est réservé à la démo loopback et doit être changé immédiatement. Ce parcours ne configure ni service public, ni routage de production, ni destination métier réelle.

## Fonctions opérationnelles

Tableau de bord et preuves des requêtes ; politique locale d’autorisation/blocage ; politique PII globale, par route et par outil avec évaluation Mirror `would_*` ; scénarios HTTP synthétiques ; audit ; mot de passe ; inventaire des interfaces, réglages listener/amont, validation, application et restauration du conteneur Envoy détenu.

Les requêtes synthétiques traversent réellement Envoy → inspecteur gRPC → destination HTTP. La console enregistre les reçus et le masquage des réponses, sans appel direct au moteur en substitution. Listener par défaut : `127.0.0.1:18082` ; inspecteur : `18101–18104` ; destination synthétique : `18090`.

## Périmètre et éditions

Community comprend politique locale, mappages HTTP/MCP explicites, signatures du relais fiable, inspection bornée des réponses/SSE et preuves locales nettoyées. Enterprise Access Broker est un pilote privé distribué séparément ; le SSO Community n’établit pas l’identité des agents et ne fournit ni délégation ni approbation.

L’inventaire NIC et la topologie sont expliqués. La démo loopback ne configure pas les adresses du système, le routage à deux cartes, les ponts transparents ou la sortie physique. Les erreurs inline bloquent. Mirror de la console observe son trajet synchrone ; le collecteur mirror séparé ne bloque pas les originaux.

## Référence locale de performance

Arrêtez la console puis mesurez séquentiellement le même trajet Envoy → inspecteur gRPC → destination HTTP synthétique.

```bash
.venv/bin/trapdefense-benchmark --scenario read --iterations 30
```

La latence p50/p95 et les décomptes JSON servent à comparer les régressions locales, pas à revendiquer un débit ou une capacité de production. Consultez [Benchmarking](docs/fr/benchmark.md).

## Documentation et vérification

[Guide de console](docs/fr/console.md) · [Architecture](docs/fr/architecture.md) · [Community / Enterprise](docs/fr/editions.md) · [Benchmarking](docs/fr/benchmark.md) · [SDK → Proxy](docs/fr/migration.md) · [Security](docs/fr/security.md)

Le code applicatif est en anglais, avec six dictionnaires UI complets. L’inspection PII hors ligne prend en charge des motifs et validateurs explicites en anglais, coréen, chinois simplifié, japonais, espagnol et français. Elle ne fournit pas de NER général pour les noms, lieux ou adresses. Chaque guide propose un choix de langue en haut.

L’inspection déterministe des secrets bloque les jetons fournisseurs reconnus, les JWT signés, les liens SAS Azure Storage et les identifiants à forte entropie dans les corps, réponses et flux SSE pris en charge. Les en-têtes d’identification ne sont transmis qu’à la destination mappée et vérifiée par signature, puis exclus de l’audit. Consultez [Security](docs/fr/security.md) pour le périmètre et les limites.

```bash
.venv/bin/python -m pytest -q
npm run check --prefix console
npm run build --prefix console
# Stop the running console before this Docker test.
TD_CONSOLE_E2E=1 .venv/bin/python -m pytest tests/test_console.py -q
```

Ce sont des vérifications synthétiques locales, pas une certification TLS/IdP client, de routage forcé en production, de HA ou de performance. La détection a des faux positifs/négatifs ; l’audit local n’est pas immuable.

## License

Community est sous MIT. Le code Enterprise privé et les actifs clients sont exclus.


## Exploitation sur un même hôte — 0.34

Connections / System affiche les PID, états et redémarrages. Dans Settings → Inspector processes, l’administrateur choisit 1, 2 ou 4 processus et applique, démarre ou arrête l’inspection. Viewer dispose d’un accès en lecture seule. L’arrêt bloque le trafic inline.

[Operations](docs/fr/operations.md) · [Inspector pool](docs/fr/inspector-pool.md)

## Pilote MCP réel (candidat local 0.35)

Exécutez initialisation, découverte et outils documentaires MCP réels via le pare-feu, avec un agent LLM local facultatif. Données synthétiques, limites explicites et latence directe/proxy.

[MCP pilot](docs/fr/mcp-pilot.md)
