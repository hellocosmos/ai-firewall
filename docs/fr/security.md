# Périmètre de sécurité et signalement

[English](../en/security.md) · [한국어](../ko/security.md) · [简体中文](../zh-CN/security.md) · [日本語](../ja/security.md) · [Español](../es/security.md) · [Français](../fr/security.md)

Signalez les vulnérabilités en privé à **hellocosmos@gmail.com** , avec révision, reproduction synthétique et impact. Ne publiez pas de données client, jetons ou identifiants réels dans les issues. Aucun SLA de réponse fixe n’est promis.

Le périmètre couvre les flux HTTP/MCP pris en charge et explicitement routés depuis un relais signé de confiance. Les exemples locaux sont synthétiques, pas des appliances de production durcies.

- Restreignez les listeners en clair, ExtProc et mirror aux réseaux et émetteurs fiables.
- Protégez et renouvelez les clés de signature ; ne les donnez jamais aux agents. Imposez le routage amont contre le contournement.
- Les défaillances inline de l’inspecteur ou de l’autorisation doivent bloquer. Le collecteur mirror séparé ne bloque pas l’original ; Mirror de la console est synchrone et bloque si la communication avec l’inspecteur échoue.
- Configurez les limites de corps/durée, les mappages et le masquage par champ. SSE avec tampon est borné, pas un streaming illimité.
- La protection anti-rejeu et l’audit SQLite local ne garantissent ni HA distribuée ni conservation immuable.
- Les signatures et la détection PII produisent des faux positifs et négatifs.
- Une source signée ne prouve pas l’identité humaine ou de l’agent. Enterprise exige une chaîne d’identité fiable distincte.

Le compte initial est `admin`, mot de passe `1234` ; changez-le dans les paramètres. La gestion écoute sur loopback. Les réglages réseau gèrent le conteneur Envoy propre à la démo, pas les adresses des interfaces du système, les routes physiques ni les règles du pare-feu. Authentification, contrôles CSRF et hachage ne transforment pas cette démo en IAM de production. MIT couvre Community ; l’implémentation privée et les actifs clients sont exclus.
