# Pool d’inspecteurs Community

[English](../en/inspector-pool.md) · [한국어](../ko/inspector-pool.md) · [简体中文](../zh-CN/inspector-pool.md) · [日本語](../ja/inspector-pool.md) · [Español](../es/inspector-pool.md) · [Français](../fr/inspector-pool.md)

Exécute 1, 2 ou 4 inspecteurs sur le même hôte et génère la configuration Envoy. La commande ne démarre pas Docker et ne remplace pas la console. Enterprise et la haute disponibilité entre hôtes sont hors périmètre.

Tous les processus partagent la même base locale anti-rejeu et le journal d’audit. N’utilisez ni bases séparées ni système de fichiers réseau. Les chemins relatifs dépendent du répertoire de lancement. Politique et clé sont figées dans une copie privée au démarrage ; toute modification impose le redémarrage du pool et la coordination avec Envoy et la source de signatures.

Chaque enfant dispose par défaut de 3 redémarrages maximum. Une fois la limite atteinte, tout le pool s’arrête. Les requêtes en échec ne sont pas renvoyées automatiquement. La panne de tous les inspecteurs ne permet pas de contourner les contrôles.

status.json contient état, PID, ports et compteurs de redémarrage. Le répertoire exige le mode 0700 et la clé doit être accessible uniquement au propriétaire. Après un arrêt forcé du superviseur, les enfants s’arrêtent aussi, mais les fichiers d’état et copies privées peuvent rester ; vérifiez PID, date et état réel.

Les ports commencent à 18101 pour gRPC et 18111 pour la santé ; le proxy utilise 18082. Docker Desktop nécessite les arguments supplémentaires ci-dessous et une publication sur loopback uniquement. Sous Linux, utilisez les valeurs par défaut et host network. L’interface de la console et le gestionnaire de services ne sont pas intégrés.

```bash
.venv/bin/trapdefense-inspector-pool \
  --config "$PWD/.runtime-state/pool-demo/inspector.yaml" \
  --key-file "$PWD/.runtime-state/pool-demo/attestation.key" \
  --state-directory "$PWD/.runtime-state/pool-supervisor" \
  --envoy-output "$PWD/.runtime-state/pool-envoy.yaml" \
  --replicas 2
```

```text
--proxy-bind 0.0.0.0 --inspector-address host.docker.internal --upstream-address host.docker.internal
```

[Complete setup and limits / English](../en/inspector-pool.md)
