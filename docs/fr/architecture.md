# Architecture et frontière de confiance

[English](../en/architecture.md) · [한국어](../ko/architecture.md) · [简体中文](../zh-CN/architecture.md) · [日本語](../ja/architecture.md) · [Español](../es/architecture.md) · [Français](../fr/architecture.md)

La console prend en charge le SSO Microsoft Entra ID à locataire unique avec les rôles Administrateur et Lecteur. L’identité de l’opérateur et l’autorisation de l’agent sont des frontières distinctes ; l’Access Broker intégré applique l’autorisation. [Entra SSO](identity.md).

```text
AI agents → TrapDefense AI Firewall → Tools / MCP servers / APIs
            Action policy · Data protection · Audit
          ← Inspected responses ←
```

## Plan de données et de contrôle

L’API authentifie l’opérateur local, conserve les politiques et sert l’UI. Envoy transfère HTTP/MCP pris en charge et appelle l’inspecteur par gRPC ExtProc pour requêtes et réponses. Chaque flux conserve sa politique initiale. Une destination HTTP synthétique sans action métier fournit des reçus. Voir l’[installation](console.md).

## Contrat de confiance

1. Imposez le routage hors de TrapDefense pour empêcher le contournement du proxy.
2. Utilisez un déchiffreur TLS existant et autorisé. La démo ne déchiffre pas le TLS de production.
3. L’adaptateur de confiance retire `x-td-*` et `x-asr-*` fournis par le client et signe ce qu’il a observé. Préservez méthode, autorité, chemin/requête, en-têtes applicatifs et corps complet. `inspection/identity.py` définit la liaison canonique et ses exclusions.
4. Gardez la clé HMAC sur le relais et l’inspecteur uniquement, jamais chez les agents. Autorisez explicitement le `source_id` gateway-only. Isolez les liens en clair et ExtProc : les exemples n’authentifient pas une écoute gRPC publique.
5. Envoy utilise un tampon complet, des limites de taille/temps et `failure_mode_allow: false`. Il retire l’attestation avant transfert. La signature lie l’original ; l’approbation persistante éventuelle lie l’empreinte de l’action après masquage.
6. Le mode gateway-only applique des règles locales explicites de route/outil/ressource/action et vérifie la source, sans établir l’identité utilisateur ni l’autorité déléguée de l’agent.
7. Le mode Broker exige des claims JWT vérifiés et évalue registry, delegation, task, resource, action et approval à usage unique ; une identité incomplète échoue en mode fermé.

Il n’existe pas d’adaptateur universel pour tout équipement TLS. L’intégration doit empêcher l’usurpation des métadonnées et restreindre l’accès direct à l’amont.

## Couverture et limites

Les routes correspondent exactement à l’autorité, la méthode, le chemin et les en-têtes requis. MCP couvre les appels JSON-RPC déclarés et versions configurées, sans certifier toutes ses fonctions. Transports arbitraires, tunnels WebSocket, corps chiffrés opaques, CONNECT libre et découverte automatique sont exclus. Seuls les champs/formats autorisés sont modifiés ; une transformation risquée est bloquée. Les signatures détectent des motifs connus bornés, sans garantir l’arrêt de toute injection. SSE met en tampon un flux complet limité, pas un flux illimité jeton par jeton.

Le collecteur mirror distinct reçoit des copies et ne peut agir sur l’original ; des en-têtes seuls donnent une couverture incomplète. Mirror de la console observe son chemin synchrone sans modifier le corps, mais une panne de communication avec l’inspecteur bloque. Distinguez ces modes dans les déploiements et rapports. Les preuves JSONL et l’audit SQLite omettent contenu original et clés, mais restent locaux et modifiables, non immuables.

## Profil réseau

La console utilise la boucle locale et Envoy amd64/arm64 fixé par digest. macOS utilise le transfert Docker Desktop vers l’hôte ; Linux, host networking. L’inventaire affiche les interfaces du système, pas les ports physiques. Routage à deux cartes, pont transparent, sortie physique imposée, IdP/TLS réels, HA et performances nécessitent des travaux distincts. Les tests optionnels agentgateway vérifient la compatibilité, pas un service de passerelle géré.
