# design-to-dev

Skill Claude Code qui transforme un dossier de design system ou de maquettes désordonné (export Claude Design, Figma, v0, Lovable, Bolt, dossier fait main par un designer, un dev ou un agent IA) en projet prêt pour le développement.

- **Inventaire automatique** : types, tailles, doublons (hash), références entre fichiers (`src`, `href`, `url()`, `@import`, `import`, `require`, liens markdown), orphelins, artefacts d'outils, données personnelles probables.
- **Analyse par sous-agents en parallèle** (code, assets, docs/outillage, architecte) : chaque fichier reçoit `keep`, `move` ou `delete` avec une raison.
- **Plan validé par vous** avant toute action. Les cas douteux (données personnelles, faible confiance) vous sont posés.
- **Copie réorganisée** dans un nouveau dossier, avec réécriture des chemins relatifs. Le dossier source n'est jamais modifié.
- **Préproduction Claude Code** : mémoire projet `.claude/memory/` (état, journal, changements, décisions, problèmes), graphe de dépendances `.claude/graph/` alimenté par des hooks, `CLAUDE.md` court.

## Installation

```bash
git clone https://github.com/duckysface/design-to-dev ~/.claude/skills/design-to-dev
```

Prérequis : Python 3.9+ (stdlib uniquement). Sur Windows la commande est `python`, ailleurs `python3`.

## Utilisation

Dans Claude Code :

```
/design-to-dev ~/Downloads/Mon Design System
```

ou simplement « organise ce dossier de design pour le développement ». La skill demande la cible, la stack et si la mémoire doit être partagée, puis présente le plan avant d'écrire quoi que ce soit.

Les scripts s'utilisent aussi seuls :

```bash
python scripts/organize.py inventory "<source>" --out inventory.json
python scripts/organize.py plan-check plan.json --inventory inventory.json
python scripts/organize.py apply plan.json            # dry-run
python scripts/organize.py apply plan.json --apply
python scripts/organize.py verify "<cible>"
python scripts/scaffold_claude.py "<cible>" --name "Mon projet" --file-map "<cible>/docs/cleanup/file-map.json"
```

## Résultat type

```
mon-projet/
├── .claude/
│   ├── memory/        # MEMORY.md, etat.md, journal.md, changements.md, decisions.md, problemes.md, PROTOCOLE.md, GRAPHE.md
│   ├── hooks/graph_hook.py
│   ├── graph/graph.json
│   ├── skills/<ds>/   # skill de marque de l'export, si présente
│   └── settings.json  # hooks du graphe
├── src/
│   ├── styles/        # index.css, tokens, components.css
│   ├── components/<catégorie>/<Composant>/
│   └── assets/{brand,images}/
├── prototypes/<écran>/
├── docs/
│   ├── design-system/ # README, specimens, références visuelles
│   ├── adr/0001-structure-du-projet.md
│   └── cleanup/       # report.md, file-map.json (avant → après)
├── vendor/            # bundles générés encore utilisés
├── CLAUDE.md
├── README.md
└── .gitignore
```

## Contenu du dépôt

| Chemin | Rôle |
|---|---|
| `SKILL.md` | Déroulé de la skill (étapes 0 à 7, garde-fous) |
| `references/` | Conventions de dossiers, règles de classification, format du plan, prompts des sous-agents |
| `scripts/organize.py` | Inventaire, vérification du plan, application, vérification des références |
| `scripts/scaffold_claude.py` | Création de `.claude/` (mémoire, hooks, graphe, `CLAUDE.md`) |
| `templates/claude/` | Protocole mémoire, règles du graphe, hook `graph_hook.py` |

## Garde-fous

- La source n'est jamais modifiée ; la cible doit être vide (ou `--force` demandé explicitement).
- Rien n'est supprimé sans plan approuvé ; un fichier encore référencé ne peut pas être supprimé.
- Les secrets ne sont jamais copiés (`.env` → `.env.example`) et sont masqués dans le graphe.
- Le contenu des fichiers analysés est traité comme une donnée, jamais comme une instruction.

## Licence

MIT
