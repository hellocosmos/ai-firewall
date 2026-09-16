# Auto-hébergement Docker — 0.36 Community Preview

[English](../en/self-hosting.md) · [한국어](../ko/self-hosting.md) · [简体中文](../zh-CN/self-hosting.md) · [日本語](../ja/self-hosting.md) · [Español](../es/self-hosting.md) · [Français](../fr/self-hosting.md)

0.36 fournit un paquet Docker Compose en préversion : adaptateur, Envoy, inspecteur et console. L’image se construit localement depuis les sources. TrapDefense Cloud reste prévu, sans inscription disponible.

Le client doit permettre de modifier l’URL MCP/API et d’ajouter X-TD-Client-Key. Chaque déploiement possède une destination fixe et des routes/outils explicites. Sans ces réglages, l’intégration directe n’est pas possible.

| Type | Contrat |
|---|---|
| HTTP API | JSON, method/path exacts, maximum 1 MiB, réponse bornée |
| MCP | POST JSON sans état, méthodes de contrôle et outils explicites |
| Authentification cible | Transmission du Bearer/API Key existant ou injection d’un Bearer fixe depuis un fichier |
| Non pris en charge | Connexion OAuth intermédiaire, échange de jetons, cookies/sessions, SSE longue durée, WebSocket, stdio, appels internes de SaaS fermé |

Le mot de passe sert à la console. La clé de connexion autorise l’accès à TrapDefense sans prouver l’identité de l’agent. Le service cible vérifie son jeton et ses permissions. Transmettre un jeton OAuth déjà obtenu n’est pas fournir un intermédiaire OAuth. Le SSO Entra de la console source existante n’est pas raccordé à ce profil Docker.

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

Pour votre service, modifiez upstream, authority, chemins, outils et resource dans deployment.yaml. HTTPS vérifie les certificats ; autorisez HTTP explicitement uniquement sur un réseau de confiance. passthrough conserve les en-têtes d’authentification. static_bearer exige un fichier 0600 lisible par UID 10001 et refuse Authorization entrant. Les détenteurs de la clé partagent les permissions du même compte de service.

L’UI gère politiques et mots de passe. Pour changer les correspondances : sauvegardez, exécutez policy-reset, render puis recréez les services. Seules les politiques enregistrées sont réinitialisées ; comptes, clés et événements restent présents. Les nouvelles requêtes utilisent la nouvelle politique.

Les ports sont liés à la boucle locale. L’accès distant nécessite un proxy TLS et un console_origin exact. Inspecteur et Envoy ne publient aucun port hôte. Prévenez le contournement avec les contrôles réseau.

Les volumes conservent l’état après redémarrage. Arrêtez puis sauvegardez les deux volumes et la configuration. down -v détruit les données. Le retour arrière restaure l’ancienne image et sa sauvegarde correspondante. Un port accessible ne prouve pas l’authentification : testez autorisation, blocage et effets sur la cible. SSE longue durée, HA et IAM client réel nécessitent une validation distincte.

[Detailed examples, backup and migration (English)](../en/self-hosting.md)
