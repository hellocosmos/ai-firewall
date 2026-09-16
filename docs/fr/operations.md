# Exploitation sur un même hôte — 0.34

[English](../en/operations.md) · [한국어](../ko/operations.md) · [简体中文](../zh-CN/operations.md) · [日本語](../ja/operations.md) · [Español](../es/operations.md) · [Français](../fr/operations.md)

Connections / System affiche les PID, états et redémarrages. Dans Settings → Inspector processes, l’administrateur choisit 1, 2 ou 4 processus et applique, démarre ou arrête l’inspection. Viewer dispose d’un accès en lecture seule. L’arrêt bloque le trafic inline.

Les processus partagent les bases locales de politiques, événements et protection antirejeu. Les nouvelles requêtes lisent la politique enregistrée ; les requêtes en cours conservent leur version jusqu’à l’inspection de la réponse. Un changement de nombre redémarre le pool et Envoy. Une restauration est tentée en cas d’échec ; si elle échoue, le trafic reste bloqué. Aucun appel d’outil n’est réessayé automatiquement.

Après trois remplacements par processus, l’épuisement des tentatives arrête tout le pool. Redémarrer le service de console relance le pool. Le pool CLI indépendant ne lit pas les politiques de console et nécessite un redémarrage complet après modification du YAML ou de la clé.

Nécessite systemd utilisateur sous Linux et les droits Docker existants. Exécutez avec le compte d’installation, sans sudo. L’installation démarre immédiatement ; la suppression conserve les données. Arrêtez d’abord la console manuelle.

```bash
./scripts/console-service.sh install
./scripts/console-service.sh status
./scripts/console-service.sh logs
./scripts/console-service.sh restart
./scripts/console-service.sh stop
./scripts/console-service.sh start
./scripts/console-service.sh remove
```

L’activation seule ne garantit pas le démarrage sans connexion : l’administrateur doit configurer Docker et un gestionnaire utilisateur persistant (linger). Sur un hôte de laboratoire Ubuntu 26.04 x86_64 avec Python 3.12, Node 22 et Docker, nous avons vérifié l’installation, un redémarrage réel avec linger, le démarrage automatique avant connexion SSH, la restauration de deux inspecteurs, la conservation des politiques/événements et le trafic synthétique autorisé, bloqué et expurgé. Les autres hôtes et la capacité en production exigent leur propre validation. Consultez le guide anglais pour les groupes Docker du gestionnaire utilisateur. La HA entre serveurs n’est pas implémentée. Ne partagez pas SQLite sur un système de fichiers réseau. Les tests synthétiques ne certifient pas la production.

[English reference](../en/operations.md) · [Inspector pool](inspector-pool.md)
