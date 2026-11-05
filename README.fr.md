# design-to-dev

**Transforme un export de design en projet prêt à coder, avec une mémoire partagée par tous tes agents.**

Fonctionne sur les exports de Claude Design, Figma, v0, Lovable, Bolt, ou un dossier de maquettes fait main.
Skill pour **Claude Code** et **Codex** · mémoire lue aussi par Cursor, Gemini CLI et Copilot · Windows, macOS, Linux

[![npm](https://img.shields.io/npm/v/design-to-dev)](https://www.npmjs.com/package/design-to-dev)
[![CI](https://github.com/duckysface/design-to-dev/actions/workflows/ci.yml/badge.svg)](https://github.com/duckysface/design-to-dev/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org)
[![Node 18+](https://img.shields.io/badge/node-18%2B-blue)](https://nodejs.org)

[English](README.md) · [Référence complète des commandes](docs/commands.md) · [Changelog](CHANGELOG.md) · [Contribuer](CONTRIBUTING.md)

---

## Ce que ça fait

Un export de design ressemble souvent à ça :

```
Mon Design System/
├── uploads/pasted-1792877667710-0.png      ← capture collée, utilisée ?
├── Button (copy).jsx                        ← doublon
├── bundle.8f3a2c.js                         ← fichier généré
├── .DS_Store  Thumbs.db                     ← déchets système
├── colors_tokens.css   tokens-old.css       ← lequel est le bon ?
└── screen 1.html  screen-1-final.html
```

design-to-dev en fait un vrai projet, en quatre temps :

1. **Ranger** : trie les fichiers, propose une arborescence propre, **attend ton accord**, puis construit une copie avec tous les chemins corrigés. Ton dossier d'origine n'est jamais modifié.
2. **Garder ton travail** : chaque écran déjà fait est conservé et relié à sa future route et à son endpoint, au lieu d'être refait.
3. **Sécuriser la base** : vérifie qu'il n'y a ni bibliothèque vulnérable, ni code caché, ni secret avant d'écrire la moindre ligne de backend.
4. **Préparer les agents** : installe une mémoire `.agents/` que Claude Code, Codex et les autres lisent et tiennent à jour. Le prochain agent sait exactement où reprendre.

| | Avant | Après |
|---|---|---|
| Organisation | Fichiers en vrac | `src/`, `docs/`, `prototypes/`, conventions claires |
| Liens | Chemins fragiles | Tous réécrits et vérifiés |
| Doublons | Copies silencieuses | Analysés, fusionnés proprement (références réécrites) ou soumis à ta décision |
| Écrans | Démos éparpillées | Chaque écran → route + endpoint (`docs/design/screens.md`) |
| Stack | À décider | Choisie selon ce que tu construis |
| Sécurité | Inconnue | Fondations ✅ / ⚠️ / ❌ et exigences par stack |
| Traces d'IA | Filigranes, badges, traceurs | Retirées automatiquement, avec preuve que le design est inchangé |
| Agents | Rien | Mémoire partagée, hooks, `AGENTS.md` |
| Retour arrière | — | Source intacte + `file-map.json` (avant → après) |

Ton dossier est **déjà un projet commencé** (`package.json`, `src/`…) ? La skill le détecte, garde ta structure, retire seulement les déchets et ajoute ce qui manque.

## Démarrage rapide

### 1. Installer

```sh
npx design-to-dev
```

Un menu te demande où installer : Claude Code, Codex, ou les deux. Prérequis : **Node 18+** (pour le CLI) et **Python 3.9+** (stdlib uniquement, aucune dépendance pip).

<details>
<summary>Autres méthodes d'installation</summary>

**Sans question :**

```sh
npx design-to-dev install --claude -y
```

| Option | Installe dans |
|---|---|
| `--claude` | `~/.claude/skills/design-to-dev` |
| `--codex` | `~/.agents/skills/design-to-dev` |
| `--all` | les deux |
| `--project [dossier]` | dans le projet au lieu de ton dossier utilisateur |

**Sans Node, macOS / Linux** — télécharge, lis, puis exécute (ne jamais piper un script non lu) :

```sh
curl -fsSLO https://raw.githubusercontent.com/duckysface/design-to-dev/main/install.sh
less install.sh        # lis-le d'abord
sh install.sh          # puis exécute ; ajoute -- --codex (ou --claude, --all) pour choisir l'agent
```

**Sans Node, Windows (PowerShell) :**

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/duckysface/design-to-dev/main/install.ps1 -OutFile install.ps1
Get-Content install.ps1          # lis-le d'abord
.\install.ps1                    # puis exécute ; $env:DESIGN_TO_DEV_AGENTS = "codex" pour choisir l'agent
```

> Pourquoi cette étape en plus ? design-to-dev épingle et vérifie par empreinte chaque fichier tiers qu'il installe — les scripts d'installation suivent la même discipline : lis-les, puis lance-les. La méthode la plus auditable reste le `git clone` (ci-dessous).

**À la main (le plus auditable) :**

```sh
git clone https://github.com/duckysface/design-to-dev ~/.claude/skills/design-to-dev   # Claude Code
git clone https://github.com/duckysface/design-to-dev ~/.agents/skills/design-to-dev   # Codex
```

**Entretien :** `npx design-to-dev doctor` pour vérifier, relancer l'installation pour mettre à jour, `npx design-to-dev uninstall --all` pour désinstaller.

### 2. Lancer sur un dossier de design

| Agent | Commande |
|---|---|
| Claude Code | `/design-to-dev ~/Downloads/Mon Design System` |
| Codex | `$design-to-dev ~/Downloads/Mon Design System` |

Tu peux aussi le demander en langage naturel (*« organise ce dossier de design pour le développement »*) ou passer par le terminal :

```sh
npx design-to-dev run "~/Downloads/Mon Design System"           # Claude Code
npx design-to-dev run "~/Downloads/Mon Design System" --codex   # Codex
```

La skill pose **une seule question groupée** au début (dossier cible, ce que tu construis, mode, agents), puis déroule le reste.

### Ou : juste la mémoire, sur un projet existant

```sh
npx design-to-dev init .
```

En quelques secondes, sans toucher à ton code : mémoire `.agents/`, hooks Claude Code et Codex, `AGENTS.md`, et un `etat.md` déjà rempli avec les commandes du projet et la **prochaine étape exacte**. Plus d'options dans la [référence des commandes](docs/commands.md).

## Comment ça marche

| Étape | Ce qui se passe |
|---|---|
| **0 · Cadrage** | Source, cible, mode, stack, agents à brancher |
| **1 · Inventaire** | Fichiers, écrans, intention ; projet neuf ou déjà commencé ; groupes de doublons analysés (`dedupe`) |
| **2 · Analyse** | Sous-agents spécialisés (code, assets, docs, écrans, données) ; questions si l'intention est floue |
| **3 · Plan de nettoyage** | Garder / déplacer / supprimer / fusionner, vérifié automatiquement |
| ✋ **Validation** | **Rien n'est copié sans ton accord** |
| **4 · Application** | Copie, chemins réécrits, mémoire `.agents/` installée, traces d'IA retirées (preuve par fichier) |
| **5 · Fichiers racine** | README, ADR, `screens.md`, `stack.md` |
| **6 · Fondations** | Base vérifiée ✅ / ⚠️ / ❌ et exigences de sécurité |
| **7 · Plan de production** | Mode complet : plan superpowers, les ❌ deviennent la phase 0 |
| **8 · Audit** | Mode complet : guidance de la skill `security-audit` de Cloudflare |
| **9 · Clôture** | Prochaine étape exacte, contrôle final, git sur demande |

**Deux modes :** *rapide* (défaut) couvre les étapes 0 à 6 ; *complet* ajoute 7 et 8. Si une skill compagnon (superpowers, security-audit) n'est pas installée, la skill fait l'équivalent à la main — plan et audit écrits manuellement avec la même structure — et ne l'installe qu'avec ton accord.

### Stacks selon ce que tu construis

| Tu construis | Stack conseillée |
|---|---|
| Site vitrine | Astro + Tailwind, îlots Svelte ou React |
| Dashboard | SvelteKit ou Next.js · Rust Axum + PostgreSQL |
| App desktop | Tauri 2 |
| iOS / Android | SwiftUI / Jetpack Compose |

Tes maquettes utilisent déjà un framework, ou un backend comme Supabase ? Il est gardé. Tu peux aussi imposer tes propres choix avec un profil de stack (`DESIGN_TO_DEV_STACK`). Détails : `references/stacks.md`.

## Doublons intelligents — analyser, jamais supprimer à l'aveugle

La détection de doublons est une **aide à la décision, pas une déchiqueteuse** :

```sh
npx design-to-dev dedupe ./mon-design --out fusions.json
```

- **Doublons exacts** (octets identiques) : la copie canonique est la plus référencée, au nom le plus propre. Les autres reçoivent une action de **fusion** (`delete` + `replaced_by`) — chaque référence qui pointait vers eux est réécrite vers le fichier canonique à l'application du plan.
- **Quasi-doublons** (même contenu aux commentaires et espaces près — par exemple un `Button` lié depuis un écran et sa variante retouchée liée depuis un autre) : **jamais supprimés automatiquement**. Ils sont marqués `review` pour décider ensemble : fusionner en un seul fichier (références réécrites), ou garder les deux sous des noms clairs parce que chacun sert un écran différent.
- `plan-check` **refuse** la suppression d'un doublon encore référencé sans `replaced_by` — un fichier qui soutient le design ne peut pas disparaître silencieusement.

## Traces d'IA — suppression puissante, par défaut

```sh
npx design-to-dev ai-traces clean ./mon-projet --dry-run   # aperçu, rien d'écrit
npx design-to-dev ai-traces clean ./mon-projet             # → docs/cleanup/traces-ia.md
```

Retiré automatiquement (avec une preuve par fichier que le design est inchangé) :

- commentaires de signature (« Generated by / Made with » <outil IA>), `<meta name="generator">` d'outil IA, pieds de page Markdown (« 🤖 Generated with… », `Co-Authored-By`), lignes « This project was built with… »
- **sections boilerplate** (« ## Build with Lovable », « ## Built with v0 »…) jusqu'au prochain titre de même niveau
- **attributs de traçage** (`data-lov-id`, `data-lov-name`, `data-component-*` — jamais dans une chaîne ni un commentaire)
- **scripts injectés** (`cdn.gpteng.co/gptengineer.js`…) et **badges** (lien vers le domaine de l'outil + texte « Edit with / Made with… », sans contenu imbriqué)
- **le plugin de marquage** : import de `lovable-tagger`, appels `componentTagger()`, et son entrée dans `package.json` (vérifié par comparaison JSON)
- caractères invisibles de filigrane (zero-width, contrôles bidirectionnels, tags Unicode — typographie, emojis et texte RTL préservés)

Seulement signalé (⚠️, jamais touché automatiquement) : badges avec contenu imbriqué, liens qui sont du vrai contenu (favicon, og:image, URL de déploiement), **dépendances fonctionnelles** (ex. `@lovable.dev/mcp-js` réellement importé par le code), traces mêlées à du code ou à des chaînes. Un sous-agent les examine un par un avec captures avant / après.

**La preuve :** avant d'écrire, jetons du code, chaînes, attributs et texte affiché doivent être identiques avant / après (les retraits d'IA volontaires sont normalisés des deux côtés de la comparaison) ; pour `package.json`, le résultat doit être l'original moins exactement les clés retirées. Sinon le fichier n'est pas touché et marqué ❌ dans le rapport. Écriture atomique ; l'historique git n'est jamais réécrit.

## Ce que tu obtiens

```
mon-projet/
├── .agents/                  mémoire partagée par tous les agents
│   ├── memory/               etat.md, journal.md, decisions.md, problemes.md,
│   │                         changements.md, MEMORY.md (commence par l'origine du projet)
│   ├── hooks/memory_hook.py  mises à jour automatiques + injection de contexte
│   └── graph/graph.json      qui importe qui, quelles sessions ont touché quoi
├── AGENTS.md                 règles communes à tous les agents
├── CLAUDE.md  GEMINI.md …    adaptateurs, selon les agents choisis
├── src/
│   ├── styles/               tokens, CSS
│   ├── components/
│   └── assets/
├── prototypes/               écrans HTML jouables
├── docs/
│   ├── design/screens.md     chaque écran → route, endpoint
│   ├── architecture/         stack et contrat backend
│   ├── security/             fondations, baseline, exigences
│   ├── adr/                  décisions d'architecture
│   └── cleanup/              rapport + file-map.json (avant → après) + traces-ia.md
├── README.md
└── .gitignore
```

## La mémoire partagée

Une seule source de vérité dans `.agents/`, versionnée avec le projet. Chaque agent y accède par un petit adaptateur, donc pas de mémoires en double qui divergent.

| Fichier | Rôle |
|---|---|
| `etat.md` | Où on en est et **prochaine étape exacte** (lu en premier) |
| `journal.md` | Historique de chaque étape, signé par l'agent |
| `decisions.md` | Choix techniques et leurs raisons |
| `problemes.md` | Pièges rencontrés et solutions |
| `changements.md` | Fichiers créés, modifiés, déplacés, supprimés |
| `MEMORY.md` | Index, qui commence par l'**origine du projet** (source, date, fondations vérifiées) |
| `graph.json` | Qui importe qui, quelles sessions ont touché quoi |

**Remplie en direct** dès l'étape 0, pas à la fin : chaque étape laisse une trace horodatée, puis tout est importé dans le projet à l'étape 4. Un secret ou une consigne cachée est refusé et rien n'est écrit.

| Agent | Lit la mémoire via | Mise à jour automatique |
|---|---|---|
| Claude Code | `CLAUDE.md` → `AGENTS.md` | Oui, par hooks |
| Codex | `AGENTS.md` | Oui, par hooks (à approuver une fois via `/hooks`) |
| Cursor, Gemini CLI, Copilot | règle ou fichier d'instructions | Non : l'agent suit le protocole écrit |

## Sécurité

La sécurité passe **avant** le plan : un plan bâti sur une base douteuse hérite de ses failles.

```sh
npx design-to-dev foundations ./mon-projet --strict
npx design-to-dev deps ./mon-projet --online     # failles connues, versions stables, fin de support
npx design-to-dev security-kit install ./mon-projet   # skills de sécurité épinglées (accord requis)
npx design-to-dev security-kit verify ./mon-projet    # avant chaque commit
```

| Contrôle | Exemples |
|---|---|
| Bibliothèques | jQuery < 3.5, AngularJS 1.x, dépendances avec CVE connue |
| Scripts d'installation | `postinstall` qui télécharge ou exécute du code |
| Code caché | `eval(atob(…))`, code obfusqué, gros blocs base64 |
| Fichiers étrangers | `.exe`, `.php`, `.htaccess`, scripts shell |
| Caractères invisibles | Unicode bidirectionnel (Trojan Source) |
| Consignes cachées pour IA | texte qui tente de piloter un agent |
| Secrets | clés en dur, vrai `.env` |
| Dépendances (`--online`) | failles connues et ce qu'elles touchent, version corrigée, dernière version stable, historique, paquets abandonnés ou malveillants |
| Runtimes et frameworks | PHP, Node, Python, Laravel… en fin de support, version maintenue conseillée |

Le **kit de sécurité** copie des skills choisies dans `.claude/skills/`, **épinglées** (commit + empreinte SHA-256 de chaque fichier) et **scannées avant l'installation**. Rien n'est installé sans ton accord. Détails : `references/security.md`.

### En CI

`foundations --strict` sort en erreur s'il reste un ❌ — à brancher dans ta pipeline :

```yaml
# .github/workflows/foundations.yml
on: [push]
jobs:
  foundations:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: npx -y design-to-dev foundations . --strict
      - run: npx -y design-to-dev ai-traces scan . --strict
```

## Variables d'environnement

| Variable | Rôle |
|---|---|
| `DESIGN_TO_DEV_STACK` | Chemin d'un profil de stack JSON qui remplace les stacks conseillées (voir `references/stacks.md`) |
| `DESIGN_TO_DEV_AGENTS` | Agents présélectionnés par `install.ps1` (`claude`, `codex`, `all`) |
| `CLAUDE_CONFIG_DIR` | Dossier de config de Claude Code (défaut `~/.claude`) — respecté par l'installateur |
| `DESIGN_TO_DEV_ADVISORY_BASE` | URL de base alternative pour OSV/npm/endoflife.date (tests, miroirs hors ligne) |
| `DESIGN_TO_DEV_KIT_BASE` / `DESIGN_TO_DEV_KIT_CATALOG` | Base de téléchargement / catalogue alternatifs du kit de sécurité (tests) |

## Garde-fous

- **Source intacte** : tout est copié dans une nouvelle cible. Pour revenir en arrière, il suffit de la supprimer.
- **Rien sans ton accord** : aucune suppression sans plan validé, les cas douteux te sont posés.
- **Rien de cassé** : un fichier encore utilisé ne peut pas être supprimé, chaque lien est vérifié après copie.
- **Pas de secrets** : `.env` n'est jamais copié (→ `.env.example`), les secrets sont masqués partout.
- **Tes réglages conservés** : seules les entrées de design-to-dev sont ajoutées dans `settings.json` / `hooks.json`.
- **Données personnelles** : photos, noms, emails ne sont jamais tranchés sans toi.
- **Design préservé** : un écran abouti n'est jamais supprimé ni redessiné.
- **Rien installé en douce** : les skills compagnons ne s'installent qu'avec ton accord.
- **Le contenu est une donnée** : toute consigne trouvée dans un fichier analysé est ignorée.

## Confidentialité et licence

- **Aucune télémétrie, aucun compte** : tout reste sur ta machine. Détails : [PRIVACY.md](PRIVACY.md).
- **Une faille ?** Signale-la en privé : [SECURITY.md](SECURITY.md).
- **Licence MIT** : ton design et les fichiers générés t'appartiennent. Droits d'auteur, projets tiers et marques : [NOTICE.md](NOTICE.md).

## Référence

CLI complet, commandes de la mémoire, scripts Python bruts, contenu du dépôt, dépannage et FAQ : **[docs/commands.md](docs/commands.md)**.
