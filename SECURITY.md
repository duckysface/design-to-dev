# Politique de sécurité

## Versions suivies

Seule la dernière version publiée sur npm reçoit des correctifs de sécurité.

| Version | Suivie |
|---|---|
| 2.3.x | ✅ |
| < 2.3 | ❌ (mets à jour : `npx design-to-dev install`) |

## Signaler une faille

**N'ouvre pas d'issue publique.** Signale-la en privé :

1. Va sur [Security → Report a vulnerability](https://github.com/duckysface/design-to-dev/security/advisories/new).
2. Décris le problème, comment le reproduire, et son impact.
3. N'y mets aucun secret réel ni donnée personnelle.

Tu reçois une première réponse sous 7 jours. Une fois le correctif publié, la faille est rendue publique et tu es crédité si tu le souhaites.

## Ce qui nous intéresse

- Un script qui écrit **en dehors** du dossier cible ou modifie le dossier source.
- Un secret qui **échappe au masquage** et se retrouve dans un rapport, le graphe ou la mémoire.
- Une consigne cachée dans un fichier analysé qui parvient à **piloter l'agent**.
- Un hook qui exécute du code non prévu, ou une fusion de `settings.json` / `hooks.json` qui écrase tes réglages.
- Un problème dans les scripts d'installation.

## Hors périmètre

- Les faux positifs ou faux négatifs des contrôles (`foundations`, `security`) : ce sont des détections de candidats, pas des garanties. Ouvre une issue normale.
- Les failles des skills compagnons (superpowers, security-audit) : signale-les à leurs auteurs.
- Les failles du projet que tu analyses avec design-to-dev.

## Limites de l'outil

design-to-dev pose une base saine ; ce n'est **ni un pen-test ni un audit**. Un projet marqué ✅ peut encore contenir des failles. Avant une mise en production, fais réaliser un audit complet.
