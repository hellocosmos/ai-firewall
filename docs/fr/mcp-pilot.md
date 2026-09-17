# Pilote MCP réel — candidat local 0.35

[English](../en/mcp-pilot.md) · [한국어](../ko/mcp-pilot.md) · [简体中文](../zh-CN/mcp-pilot.md) · [日本語](../ja/mcp-pilot.md) · [Español](../es/mcp-pilot.md) · [Français](../fr/mcp-pilot.md)

Connecte le client et le serveur documentaire officiels MCP Python SDK 1.30.0 au chemin Envoy existant. Le protocole et les modifications SQLite sont réels ; les documents et attaques sont synthétiques. Ce pilote ne certifie aucun déploiement client et ne fournit pas de SDK applicatif.

Depuis la racine du dépôt, utilisez Python 3.11+ et Docker actif. Choisissez un nouveau répertoire à chaque exécution ; un répertoire existant ne sera pas écrasé.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,pilot]'
docker pull envoyproxy/envoy@sha256:57e14a549d7bd43c8d3f6d03e8cfa653e037d4b38e133acd9b54f38c524401b4
.venv/bin/python -m examples.mcp_pilot --state-dir .runtime-state/mcp-pilot-run --samples 30
```

Client → adaptateur local authentifié avec signature → Envoy/inspecteur AI Firewall → serveur MCP. L’agent ne reçoit pas la clé de signature. Le jeton autorise l’accès local sans vérifier l’identité de l’utilisateur ou de l’agent. Loopback et processus du même utilisateur ne constituent pas une isolation de production ; le routage doit empêcher le contournement.

Vérifie initialisation, découverte, lecture/écriture, suppression refusée avec conservation du document, expurgation des adresses e-mail et rejet des secrets fictifs en requête/réponse, réponse malveillante connue, outil inconnu, requête non signée et absence d’exécution lors d’une panne de l’inspecteur. Corps limité à 64 KiB. Seul Streamable HTTP JSON sans état est validé ; SSE persistant, OAuth et serveurs arbitraires exigent d’autres tests.

**Une instruction malveillante sémantique hors signatures passe intacte et est enregistrée comme known_detection_miss. Un refus du modèle ne prouve pas la détection par le pare-feu. Le blocage d’une réponse intervient après l’exécution de l’outil et n’annule pas ses effets. Des lectures bénignes répétées ne prouvent ni taux général de faux positifs ni capacité en entreprise.**

Pour un LLM réel, démarrez un modèle local capable d’appeler des outils et indiquez explicitement son URL et son nom. Le programme ne télécharge ni ne choisit le modèle et ne le remplace pas par un scénario scripté. Un modèle distant exige un tunnel local autorisé configuré séparément.

```bash
.venv/bin/python -m examples.mcp_pilot \
  --state-dir .runtime-state/mcp-agent-run --samples 30 \
  --model-url http://127.0.0.1:11434/v1 --model qwen3:1.7b
```

report.json distingue choix des outils, effets réels, motifs du pare-feu, erreurs du modèle et cas non exécutés, sans texte original ni clé. Six tours et huit appels au maximum par tâche, sans répéter un appel identique. Les processus/conteneurs créés sont arrêtés ; journaux, bases et clés privés restent dans le répertoire. Relisez le rapport avant partage. Consultez le [guide anglais](../en/mcp-pilot.md) pour les limites, variables d’authentification et commandes de régression.
