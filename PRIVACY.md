# Confidentialité

*Dernière mise à jour : 25 octobre 2026*

design-to-dev est un outil local. Il ne collecte, ne stocke et ne transmet **aucune donnée** à son auteur.

## En bref

- **Aucune télémétrie** : pas de statistiques d'usage, pas de rapport de crash, pas de traceur.
- **Aucun compte** : rien à créer, rien à connecter.
- **Tout reste sur ta machine** : les fichiers analysés, les rapports et la mémoire `.agents/` sont écrits uniquement dans les dossiers que tu choisis.
- **Ton dossier d'origine n'est jamais modifié** : la skill travaille sur une copie.

## Ce qui se passe sur ta machine

Les scripts lisent les fichiers du dossier que tu leur donnes et écrivent :

| Où | Quoi |
|---|---|
| Le dossier cible | Le projet réorganisé, `docs/`, la mémoire `.agents/` |
| Le dossier temporaire de l'agent | Inventaires et mémoire de préproduction, avant que la cible existe |
| Ton dossier de skills | Les fichiers de la skill elle-même (`~/.claude/skills`, `~/.agents/skills`) |
| La config de l'agent dans le projet | Hooks dans `.claude/settings.json` et `.codex/hooks.json` (seules nos entrées sont ajoutées) |

## Quand le réseau est utilisé

design-to-dev ne contacte aucun serveur de lui-même. Le réseau sert seulement dans ces cas, tous déclenchés par toi :

| Action | Contacte |
|---|---|
| Installation (`npx`, `install.sh`, `install.ps1`, `git clone`) | npm et GitHub |
| `foundations --run-audits` | Les registres de `npm audit`, `cargo audit` ou `osv-scanner`, s'ils sont installés |
| Installation d'une skill compagnon (superpowers, security-audit) | GitHub, **uniquement avec ton accord** |

## Ton agent d'IA

La skill tourne **dans** ton agent (Claude Code, Codex…). Pour faire son travail, l'agent lit le contenu de tes fichiers et l'envoie au fournisseur de son modèle (Anthropic, OpenAI…). Ce traitement relève de la politique de confidentialité de ce fournisseur, pas de design-to-dev. Ne donne pas à l'agent un dossier que tu ne veux pas lui confier.

## Secrets et données personnelles

- Le fichier `.env` n'est **jamais copié** ; un `.env.example` sans valeurs le remplace.
- Les secrets repérés (clés, jetons, mots de passe, identifiants dans les URL) sont **masqués** dans les rapports, le graphe et la mémoire.
- La mémoire **refuse** toute entrée qui contient un secret ou une consigne cachée : rien n'est écrit.
- Les fichiers qui semblent contenir des données personnelles (photos de personnes, noms, emails, captures de conversations) ne sont **jamais triés sans toi**.

Ces protections réduisent les risques sans les supprimer : relis ce que tu versionnes.

## Mémoire partagée ou privée

Par défaut, `.agents/memory/` est versionné avec le projet pour que toute l'équipe et tous les agents en profitent. Si tu préfères la garder pour toi :

```bash
python scripts/scaffold_memory.py <projet> --private-memory
```

Elle est alors ajoutée au `.gitignore`.

## Tes responsabilités

Si ton design contient des données personnelles réelles (clients, utilisateurs), c'est toi qui restes responsable de leur traitement, notamment au sens du RGPD. Préfère des données fictives dans les maquettes.

## Contact

Une question sur la confidentialité : ouvre une [issue sur GitHub](https://github.com/duckysface/design-to-dev/issues). Pour un problème de sécurité, suis plutôt [SECURITY.md](SECURITY.md).
