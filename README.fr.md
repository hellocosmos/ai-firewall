# TrapDefense — AI Firewall pour les agents

[English](README.md) · [한국어](README.ko.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md)

**Contrôlez les actions de l’IA. Protégez vos données.**

TrapDefense Community est un AI Firewall auto-hébergé avec console locale. Inspectez les appels HTTP et MCP pris en charge, appliquez les politiques d’action, masquez les données sensibles et conservez les preuves des décisions. L’ancien SDK reste dans [agent-runtime-security](https://github.com/hellocosmos/agent-runtime-security).

```text
AI agents → TrapDefense AI Firewall → Tools / MCP servers / APIs
            Action policy · Data protection · Audit
          ← Inspected responses ←
```

Flux logique du produit. Consultez l’[architecture de déploiement](docs/fr/architecture.md) pour les exigences de transfert de confiance, de visibilité du trafic et de routage.

## Installer et ouvrir la console

Prérequis : Python 3.11+, Node.js 22.12+ ou 24, npm et Docker Engine/Desktop local. Installation depuis les sources ; aucune publication PyPI n’est impliquée.

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall
./scripts/install-console.sh
./scripts/run-console.sh
```

Ouvrez [http://127.0.0.1:5176](http://127.0.0.1:5176). Connectez-vous avec `admin` / `1234`, puis changez le mot de passe dans les paramètres. L’anglais est la langue par défaut. Le sélecteur fonctionne avant et après connexion ; le navigateur mémorise votre choix.

## Fonctions opérationnelles

Tableau de bord et preuves des requêtes ; politique locale d’autorisation/blocage et PII ; scénarios HTTP synthétiques ; audit ; mot de passe ; inventaire des interfaces, réglages listener/amont, validation, application et restauration du conteneur Envoy détenu.

Les requêtes synthétiques traversent réellement Envoy → inspecteur gRPC → destination HTTP. La console enregistre les reçus et le masquage des réponses, sans appel direct au moteur en substitution. Listener par défaut : `127.0.0.1:18082` ; inspecteur : `18081` ; destination synthétique : `18090`.

## Périmètre et éditions

Community comprend politique locale, mappages HTTP/MCP explicites, signatures du relais fiable, inspection bornée des réponses/SSE et preuves locales nettoyées. Enterprise Access Broker est distribué séparément ; Community ne prouve pas l’identité utilisateur/agent et ne fournit ni délégation ni approbation.

L’inventaire NIC et la topologie sont expliqués. La démo loopback ne configure pas les adresses du système, le routage à deux cartes, les ponts transparents ou la sortie physique. Les erreurs inline bloquent. Mirror de la console observe son trajet synchrone ; le collecteur mirror séparé ne bloque pas les originaux.

## Documentation et vérification

[Guide de console](docs/fr/console.md) · [Architecture](docs/fr/architecture.md) · [Community / Enterprise](docs/fr/editions.md) · [SDK → Proxy](docs/fr/migration.md) · [Security](docs/fr/security.md)

Le code applicatif est en anglais, avec six dictionnaires UI complets. Les fixtures de sécurité dans d’autres langues vérifient les entrées internationales. Chaque guide propose un choix de langue en haut.

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
