# Auto-hébergement Docker — 0.38 Community Preview

[English](../en/self-hosting.md) · [한국어](../ko/self-hosting.md) · [简体中文](../zh-CN/self-hosting.md) · [日本語](../ja/self-hosting.md) · [Español](../es/self-hosting.md) · [Français](../fr/self-hosting.md)

0.38 fournit adaptateur, Envoy, inspecteur, console et authentifications séparées pour passerelle et cible. L’image se construit localement depuis les sources. TrapDefense Cloud reste prévu.

Le client doit pouvoir modifier l’URL MCP/API et utiliser `X-TD-Client-Key` ou un JWT Bearer OAuth. Chaque déploiement possède une cible fixe et des routes/outils explicites. Consultez la [matrice de compatibilité](gateway-compatibility.md).

| Type | Contrat |
|---|---|
| HTTP API | JSON, method/path exacts, maximum 1 MiB, réponse bornée |
| MCP | POST JSON sans état, méthodes de contrôle et outils explicites |
| Authentification passerelle | Clé ou JWT RS256 d’un IdP externe avec issuer/audience/scope et métadonnées RFC 9728 |
| Authentification cible | none, Bearer hérité transmis, Bearer/API Key fixe depuis fichier |
| Non pris en charge | Émission OAuth, connexion intermédiaire, DCR, OBO, cookies/sessions, SSE longue durée, WebSocket, stdio, SaaS interne fermé |

Le mot de passe sert à la console. La clé ou le JWT authentifie l’accès à TrapDefense. Le JWT est validé pour l’audience de la passerelle et n’est pas transmis à la cible, qui utilise un identifiant séparé. Ce n’est ni un registre Agent IAM ni un OAuth Authorization Server.

## Docker

Git et Docker Compose v2 sont requis. init demande un mot de passe administrateur de 12 caractères minimum, sans valeur par défaut. L’exemple cible un service synthétique et ne prouve aucune intégration réelle.

```bash
git clone https://github.com/hellocosmos/ai-firewall.git
cd ai-firewall/deploy/selfhost
docker compose build app
docker compose run --rm app init
docker compose --profile smoke up -d
docker compose run --rm app client-key
```

Connectez-vous comme admin sur http://localhost:18080. Lisez la clé avec client-key et stockez-la dans les en-têtes secrets du client. La passerelle est sur http://localhost:18084 ; le jeton cible synthétique est Bearer synthetic-target-token.

Pour votre service, modifiez upstream, authority, chemins, outils et resource. `gateway_auth` accepte `client_key` ou `jwt`; `target_auth` accepte `none`, `passthrough_bearer`, `static_bearer` et `static_api_key`. JWT et passthrough sont incompatibles. Les identifiants fixes utilisent un fichier 0600 lisible par UID 10001 et refusent les entrées en conflit.

L’UI gère politiques et mots de passe. Pour changer les correspondances : sauvegardez, exécutez policy-reset, render puis recréez les services. Seules les politiques enregistrées sont réinitialisées ; comptes, clés et événements restent présents. Les nouvelles requêtes utilisent la nouvelle politique.

Les ports sont liés à la boucle locale. L’accès distant nécessite un proxy TLS et un console_origin exact. Inspecteur et Envoy ne publient aucun port hôte. Prévenez le contournement avec les contrôles réseau.

Les volumes conservent l’état après redémarrage. Arrêtez puis sauvegardez les deux volumes et la configuration. down -v détruit les données. Le retour arrière restaure l’ancienne image et sa sauvegarde correspondante. Un port accessible ne prouve pas l’authentification : testez autorisation, blocage et effets sur la cible. SSE longue durée, HA et IAM client réel nécessitent une validation distincte.

[Compatibilité et VS Code](gateway-compatibility.md) · [Detailed examples, backup and migration (English)](../en/self-hosting.md)
