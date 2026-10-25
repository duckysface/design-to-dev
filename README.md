<div align="center">

# 🎨 → 💻 design-to-dev

**Skill de pré-production — transforme n'importe quel export design (Claude Design, Figma, v0, Lovable…) en projet prêt à coder, avec une structure propre et une mémoire multi-agents déjà configurée.**

*Le nettoyage n'est qu'une étape. Le vrai produit, c'est le projet agent-ready dès le premier jour.*

Skill pour **Claude Code** et **Codex** · mémoire partagée avec Cursor, Gemini CLI, Copilot · Python 3.9+ (stdlib) · Windows, macOS, Linux

![Licence MIT](https://img.shields.io/badge/licence-MIT-green)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Dépendances](https://img.shields.io/badge/d%C3%A9pendances-aucune-brightgreen)
![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-d97757)
![Codex](https://img.shields.io/badge/Codex-skill-10a37f)
[![npm](https://img.shields.io/npm/v/design-to-dev?color=cb3837)](https://www.npmjs.com/package/design-to-dev)

</div>

---

## 🧠 Juste la mémoire ? Une commande

Ton projet est déjà rangé, ou déjà commencé ? Pas besoin du reste :

```bash
npx design-to-dev init .
```

En quelques secondes, sans toucher à ton code : mémoire `.agents/` partagée, hooks Claude Code + Codex, `AGENTS.md`, et un
`etat.md` **déjà rempli** — ce que tu construis, les commandes du projet (`pnpm install`, `pnpm run dev`…) et la **prochaine
étape exacte**, par exemple :

> Lancer le projet existant (`pnpm run dev`) et vérifier qu'il démarre, puis remplacer les données factices de
> `src/pages/OrdersPage.tsx` par l'appel `GET /api/orders`

Le prochain agent qui ouvre le projet sait où reprendre. Détails : [mémoire seule](#juste-la-mémoire-sur-un-projet-existant).

---

## 🤔 Le problème

Un export de Claude Design, Figma, v0, Lovable ou Bolt, ou un dossier monté à la main, ressemble souvent à ça :

```
Mon Design System/
├── uploads/pasted-1792877667710-0.png      ← capture collée, utilisée ?
├── Button (copy).jsx                        ← doublon
├── bundle.8f3a2c.js                         ← généré
├── .DS_Store  Thumbs.db                     ← déchets système
├── colors_tokens.css   tokens-old.css       ← lequel est le bon ?
├── screen 1.html  screen-1-final.html       ← ...
└── readme.md
```

**design-to-dev** trie tout ça, propose une arborescence propre, **attend ton accord**, puis construit une copie réorganisée avec tous les chemins corrigés. Le dossier d'origine n'est jamais touché. Le projet sort avec une **mémoire partagée** que tous tes agents de code lisent et tiennent à jour.

Le dossier est **déjà un projet commencé** (`package.json`, `src/`, lockfile…) ? La skill le détecte et passe en mode
« nettoyer + compléter l'infra agents » : elle garde ta structure, retire seulement les déchets et ajoute la mémoire, au lieu de
tout réorganiser.

Et comme tes pages et démos sont souvent déjà faites, la skill les **repère, les garde et prévoit de les brancher au backend** au lieu de les refaire. Elle devine ce que tu construis (site vitrine, dashboard, app desktop, iOS, Android), te pose la question si ce n'est pas clair, range le projet selon la stack adaptée, écrit le plan avec **superpowers** et pose une **base de sécurité** avant d'écrire le backend.

---

## ⚡ En bref

```mermaid
flowchart LR
    A["📁 Dossier de design<br/>désordonné"] --> B["🔍 Inventaire<br/>automatique"]
    B --> C["🤖 Sous-agents<br/>en parallèle"]
    C --> D["📋 Plan"]
    D --> E{"✅ Ton accord ?"}
    E -- non --> D
    E -- oui --> F["📦 Copie<br/>réorganisée"]
    F --> G["🧠 Mémoire<br/>multi-agents"]
    G --> P["🗺️ Plan<br/>superpowers"]
    P --> SEC["🔒 Sécurité"]
    SEC --> H["🚀 Prêt pour<br/>la production"]

    style A fill:#fde2e2,stroke:#e57373,color:#000
    style E fill:#fff4cc,stroke:#f0b400,color:#000
    style H fill:#d9f7e3,stroke:#34a853,color:#000
```

| | Avant | Après |
|---|---|---|
| 🗂️ Organisation | Fichiers en vrac, noms au hasard | `src/`, `docs/`, `prototypes/`, conventions claires |
| 🧹 Propreté | Doublons, artefacts, déchets système | Seulement ce qui sert, avec la raison de chaque suppression |
| 🔗 Liens | Chemins fragiles | Tous les chemins réécrits et vérifiés (0 lien cassé) |
| 🧠 Agents | Rien | Mémoire `.agents/` partagée, graphe, hooks Claude Code + Codex, `AGENTS.md` |
| 🖥️ Écrans | Démos éparpillées | Chaque écran gardé, relié à sa route et à son endpoint (`docs/design/screens.md`) |
| 🧱 Stack | À décider | Arborescence adaptée à l'intention (Astro, SvelteKit + Axum, Tauri, SwiftUI, Compose) |
| 🗺️ Plan | Aucun | Plan de production superpowers : brancher l'existant, ajouter ce qui manque |
| 🔒 Sécurité | Inconnue | Base CWE/ASVS, exigences par stack, audit Cloudflare avant la prod |
| ↩️ Retour arrière | — | Source intacte + `file-map.json` (avant → après) |

---

## 📥 Installation

Choisis ta méthode. Chacune te laisse choisir l'agent : **Claude Code**, **Codex**, ou les deux.

### Avec npm / npx (recommandé)

```bash
npx design-to-dev
```

Un menu demande où installer. Installation globale possible : `npm i -g design-to-dev` puis `design-to-dev`. Sans question :

```bash
npx design-to-dev install --claude -y
```

| Option | Installe dans |
|---|---|
| `--claude` | `~/.claude/skills/design-to-dev` (ou `$CLAUDE_CONFIG_DIR/skills/…`) |
| `--codex` | `~/.agents/skills/design-to-dev` (dossier de skills lu par Codex) |
| `--all` | les deux |
| `--project [dossier]` | dans le projet (`.claude/skills`, `.agents/skills`) au lieu de ton dossier utilisateur |

### Sans Node, en une ligne

macOS / Linux :

```bash
curl -fsSL https://raw.githubusercontent.com/duckysface/design-to-dev/main/install.sh | sh
```

Agent précis : `… | sh -s -- --codex` (ou `--claude`, `--all`).

Windows (PowerShell) :

```powershell
irm https://raw.githubusercontent.com/duckysface/design-to-dev/main/install.ps1 | iex
```

Agent précis : `$env:DESIGN_TO_DEV_AGENTS = "codex"` avant la commande (`claude`, `codex` ou `all`).

### À la main

```bash
git clone https://github.com/duckysface/design-to-dev ~/.claude/skills/design-to-dev   # Claude Code
git clone https://github.com/duckysface/design-to-dev ~/.agents/skills/design-to-dev   # Codex
```

Seul prérequis à l'usage : Python 3.9+ (`python` sur Windows, `python3` ailleurs).

| Action | Commande |
|---|---|
| Vérifier Python et les installations | `npx design-to-dev doctor` |
| Mettre à jour | relancer l'installation |
| Désinstaller | `npx design-to-dev uninstall --all` |

## ▶️ Utilisation

| Agent | Commande |
|---|---|
| Claude Code | `/design-to-dev ~/Downloads/Mon Design System` |
| Codex | `$design-to-dev ~/Downloads/Mon Design System` |

ou en langage naturel : *« organise ce dossier de design pour le développement »*.

La skill te pose d'abord **une seule question groupée** (cible, ce que tu veux construire, mémoire partagée ou privée, agents à brancher), puis déroule le reste.

Ou directement depuis ton terminal : la commande installe la skill si besoin, puis lance l'agent.

```bash
npx design-to-dev run "~/Downloads/Mon Design System"            # Claude Code
npx design-to-dev run "~/Downloads/Mon Design System" --codex    # Codex
npx design-to-dev run "~/Downloads/Mon Design System" --print    # affiche juste la commande
```

Les outils d'analyse marchent aussi seuls, sans agent :

| Commande | Ce qu'elle fait |
|---|---|
| `npx design-to-dev scan <dossier>` | intention, écrans et démos existants, contrat backend, stack conseillée |
| `npx design-to-dev security <dossier>` | candidats de sécurité (CWE + ASVS + correctif), secrets masqués |
| `npx design-to-dev requirements --intent dashboard` | checklist de sécurité pour la stack |
| `npx design-to-dev skills` | superpowers et security-audit installées ? sinon, comment les installer |
| `npx design-to-dev inventory <dossier>` | inventaire brut des fichiers |
| `npx design-to-dev path` | dossier de la skill installée |

### Juste la mémoire, sur un projet existant

Pas besoin de passer par le nettoyage. `init` analyse le projet en lecture seule et pré-remplit `etat.md` (objectif détecté,
commandes, prochaine étape, points de vigilance) ; un `etat.md` existant n'est jamais écrasé.

```bash
npx design-to-dev init .                                   # claude + codex
npx design-to-dev init . --agents claude,codex,cursor
npx design-to-dev init . --next-step "Créer le monorepo avec apps/web et packages/ui"
npx design-to-dev init . --inventory design-inventory.json # reprend un scan déjà fait
npx design-to-dev init . --no-detect                       # etat.md vierge, à remplir
npx design-to-dev init . --check                           # contrôle sans rien écrire
npx design-to-dev init . --update                          # met à jour le hook
```

---

## 🔄 Comment ça marche

```mermaid
flowchart TD
    S0["<b>0 · Cadrage</b><br/>source, cible, intention, mémoire, agents"]
    S1["<b>1 · Inventaire + détection</b><br/>fichiers, doublons, écrans,<br/>intention, contrat backend"]
    S2["<b>2 · Analyse</b><br/>équipes nettoyage + design<br/>(questions si intention floue)"]
    S3["<b>3 · Plan</b><br/>keep / move / delete<br/>+ vérification automatique"]
    OK{"<b>Validation</b><br/>par toi"}
    S4["<b>4 · Application</b><br/>copie + réécriture des chemins"]
    S5["<b>5 · Fichiers racine</b><br/>README, ADR, screens.md, stack.md"]
    S6["<b>6 · Mémoire</b><br/>.agents/ : mémoire, graphe, hooks<br/>+ adaptateurs par agent"]
    S7["<b>7 · Plan</b><br/>superpowers : brancher l'existant"]
    S8["<b>8 · Sécurité</b><br/>base CWE/ASVS + exigences<br/>+ audit Cloudflare"]
    S9["<b>9 · Git</b><br/>premier commit (sur demande)"]

    S0 --> S1 --> S2 --> S3 --> OK
    OK -- "à corriger" --> S3
    OK -- "oui" --> S4 --> S5 --> S6 --> S7 --> S8 --> S9

    style OK fill:#fff4cc,stroke:#f0b400,color:#000
    style S4 fill:#e3f0ff,stroke:#4a90d9,color:#000
    style S6 fill:#efe3ff,stroke:#8e5cd9,color:#000
```

### 🤖 L'analyse par sous-agents

Chaque spécialiste reçoit sa part de l'inventaire et renvoie, pour chaque fichier, une action, une destination, une raison et un niveau de confiance. Si l'agent ne sait pas lancer de sous-agents, il fait les mêmes passes l'une après l'autre.

```mermaid
flowchart TB
    INV[("📄 inventory.json")]
    INV --> CODE["🧩 code<br/>composants, tokens, écrans"]
    INV --> ASSETS["🖼️ assets<br/>images, polices, captures"]
    INV --> DOCS["📚 docs-tooling<br/>markdown, specimens, configs"]
    INV --> ARCH["🏛️ architect<br/>stack, arborescence, ADR"]
    DINV[("📄 design-inventory.json")]
    DINV --> SCR["🖥️ screens<br/>écrans, démos, doublons, manquants"]
    DINV --> CMP["🧱 components<br/>composants, tokens"]
    DINV --> DATA["🔌 data-contract<br/>entités, endpoints, auth"]
    DINV --> INT["🎯 intent<br/>ce que tu construis"]
    DINV --> ADP["🔁 stack-adapter<br/>écran → route de la stack"]
    CODE & ASSETS & DOCS & ARCH --> PLAN[("📋 plan.json")]
    SCR & CMP & DATA & INT & ADP --> SCREENS[("🗂️ docs/design/screens.md")]
    PLAN --> REVIEW["❓ cas douteux : te sont posés"]
```

### 🛡️ Ce que `plan-check` refuse

Avant toute copie, le plan est vérifié automatiquement. Il est **refusé** si :

| ❌ | Cas refusé |
|---|---|
| 1 | un fichier n'a pas d'action, ou en a plusieurs |
| 2 | un fichier supprimé est encore utilisé (`src`, `href`, `import`…) sans remplaçant |
| 3 | deux fichiers arrivent au même endroit, ou un chemin serait à la fois fichier et dossier |
| 4 | une destination sort de la cible |

---

### 🧱 Stacks selon ce que tu construis

| Intention | Stack conseillée |
|---|---|
| Site vitrine | Astro + Tailwind + Motion/GSAP, îlots Svelte ou React, Rust Axum si formulaires |
| Dashboard (admin + utilisateurs) | SvelteKit ou Next.js, TanStack Query, shadcn/ui · Rust Axum + SQLx + PostgreSQL · Argon2id, cookies HttpOnly, MFA TOTP |
| App desktop | Tauri 2 (SQLite, trousseau OS, IPC minimal, updater signé) |
| iOS / Android | SwiftUI / Jetpack Compose, cœur Rust partagé via UniFFI |

Si tes maquettes utilisent déjà un framework, la skill te demande : le garder ou le porter. Détails : [`references/stacks.md`](references/stacks.md).

### 🔒 Sécurité, avant d'écrire le backend

Méthode reprise de [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) (un motif repéré n'est qu'un *candidat*, pas une faille) et contrôles ancrés dans OWASP ASVS 4.0.3 et les CWE, comme [UnitOneAI/SecuritySkills](https://github.com/UnitOneAI/SecuritySkills) :

1. `security` repère les motifs à risque (XSS, SQL concaténé, jetons dans `localStorage`, secrets en dur, Tauri/Electron/Android/iOS mal configurés…) → `docs/security/baseline.json`.
2. `requirements` écrit la checklist de la stack et des écrans détectés (connexion → anti brute-force, upload → contrôle MIME…) → `docs/security/exigences.md`.
3. Chaque exigence devient une tâche testée dans le plan superpowers.
4. Avant la prod : skill `security-audit` de Cloudflare (installée seulement si tu le veux).

## 📂 Résultat type

```
mon-projet/
├── .agents/                     ← partagé par tous les agents
│   ├── memory/                  état, journal, décisions, problèmes, protocole
│   ├── graph/graph.json         graphe des fichiers et de leurs dépendances
│   ├── hooks/memory_hook.py     un seul hook pour Claude Code et Codex
│   ├── skills/<ds>/             skill de marque de l'export, si présente
│   └── design-to-dev.json       manifeste (version, agents, empreinte du hook)
├── .claude/settings.json        hooks Claude Code      ┐
├── .codex/hooks.json            hooks Codex            │
├── .cursor/rules/memoire-projet.mdc                    │ selon --agents
├── .github/copilot-instructions.md                     │
├── CLAUDE.md  GEMINI.md         renvoient vers AGENTS.md ┘
├── AGENTS.md                    règles communes (bloc géré, ton contenu est conservé)
├── src/
│   ├── styles/                  index.css, tokens, components.css
│   ├── components/<catégorie>/<Composant>/
│   └── assets/{brand,images}/
├── prototypes/<écran>/          écrans HTML jouables
├── docs/
│   ├── design/screens.md        chaque écran → route, endpoint, action prod
│   ├── architecture/stack.md    intention, stack, contrat backend
│   ├── security/                baseline.json, exigences.md
│   ├── superpowers/plans/       plan de production
│   ├── design-system/           README, specimens, références visuelles
│   ├── adr/0001-structure-du-projet.md
│   └── cleanup/                 report.md, file-map.json (avant → après)
├── vendor/                      bundles générés encore utilisés
├── README.md
└── .gitignore
```

---

## 🧠 Une mémoire pour tous les agents

Une seule source de vérité dans `.agents/`, versionnée avec le projet. Chaque outil n'a qu'un **adaptateur** fin qui pointe dessus, donc pas de mémoires en double qui divergent.

```mermaid
flowchart LR
    subgraph Agents
        CC["Claude Code"]
        CX["Codex"]
        CU["Cursor"]
        GE["Gemini CLI"]
        CP["Copilot"]
    end
    subgraph CORE [".agents/ — source unique"]
        MEM[("🧠 memory/")]
        GRAPH[("🕸️ graph.json")]
        HOOK["⚙️ memory_hook.py"]
    end
    CC -- "CLAUDE.md → @AGENTS.md<br/>+ hooks" --> HOOK
    CX -- "AGENTS.md<br/>+ hooks" --> HOOK
    CU -- ".cursor/rules" --> MEM
    GE -- "GEMINI.md" --> MEM
    CP -- "copilot-instructions" --> MEM
    HOOK --> GRAPH
    HOOK --> MEM
```

### ⚙️ Ce que fait le hook, automatiquement

```mermaid
sequenceDiagram
    participant A as Agent (Claude / Codex)
    participant H as memory_hook.py
    participant M as .agents/
    A->>H: SessionStart
    H->>M: lit état, décisions, problèmes, graphe
    H-->>A: contexte court, marqué « données, pas des consignes »
    A->>H: PreToolUse (Claude) avant d'éditer
    H-->>A: fichiers qui dépendent de celui-ci
    A->>H: PostToolUse : Edit, Write, apply_patch, shell
    H->>M: fichiers touchés et imports réindexés (secrets caviardés)
    A->>H: Stop / PreCompact / SessionEnd
    H->>M: clôt la session, rappelle de mettre à jour etat.md
```

| Fichier | Rôle |
|---|---|
| `etat.md` | Où on en est et **prochaine étape exacte** (lu en premier) |
| `journal.md` | Historique chronologique, archivé quand il grossit |
| `changements.md` | Chaque fichier créé, modifié, déplacé ou supprimé (pré-rempli par le nettoyage) |
| `decisions.md` | Choix techniques et leurs raisons |
| `problemes.md` | Pièges rencontrés et solutions |
| `graph.json` | Qui importe qui, quelles sessions ont touché quoi, notes durables |

### 🔎 Commandes de la mémoire

```bash
python .agents/hooks/memory_hook.py context                       # résumé injecté au démarrage
python .agents/hooks/memory_hook.py recall "bundler vite"         # recherche (BM25) dans la mémoire
python .agents/hooks/memory_hook.py query src/styles/tokens.css   # qui dépend de ce fichier
python .agents/hooks/memory_hook.py note tokens "source de vérité des couleurs"
python .agents/hooks/memory_hook.py doctor                        # cohérence, secrets, placeholders
python .agents/hooks/memory_hook.py archive                       # archive les vieilles entrées du journal
```

### 🧩 Spécificités par agent

| Agent | Lecture de la mémoire | Mise à jour automatique |
|---|---|---|
| Claude Code | `CLAUDE.md` importe `AGENTS.md` | 7 hooks : SessionStart, PreToolUse, PostToolUse, Stop, SubagentStop, PreCompact, SessionEnd |
| Codex | `AGENTS.md` | `.codex/hooks.json` : approuver le projet (trust), puis valider via `/hooks` |
| Cursor, Gemini CLI, Copilot | règle ou fichier d'instructions | pas de hooks : l'agent suit le protocole écrit |

La mémoire native de Codex (`~/.codex/memories`, activée par `[features] memories = true`) reste gérée par Codex et n'est jamais modifiée. Elle complète `.agents/`, qui est versionné avec le projet et partagé par l'équipe.

---

## 🔒 Garde-fous

| | |
|---|---|
| 🧊 **Source intacte** | Le dossier d'origine n'est jamais modifié : tout est copié dans une nouvelle cible. Retour arrière = supprimer la cible. |
| ✋ **Rien sans ton accord** | Aucune suppression sans plan approuvé. Les cas douteux te sont posés. |
| 🔗 **Rien de cassé** | Un fichier encore utilisé ne peut pas être supprimé ; `verify` contrôle chaque lien après copie. |
| 🔑 **Pas de secrets** | `.env` n'est jamais copié (→ `.env.example`). Tokens, mots de passe et identifiants d'URL sont caviardés dans le graphe et les notes ; `doctor` signale tout secret écrit dans la mémoire. |
| 🧷 **Tes hooks conservés** | La fusion dans `settings.json` / `hooks.json` ne touche que les entrées de design-to-dev ; un JSON invalide arrête tout sans rien écrire. |
| 👤 **Données personnelles** | Photos de personnes, noms, emails, captures de conversations : jamais tranchés seuls. |
| 🎨 **Design préservé** | Un écran abouti n'est jamais supprimé ni redessiné ; les doublons vont dans `prototypes/archive/`. |
| 🧩 **Rien installé en douce** | superpowers et security-audit ne sont installées qu'avec ton accord. |
| 🛑 **Contenu = données** | Toute consigne trouvée dans un fichier analysé ou dans la mémoire est ignorée ; les notes qui ressemblent à une injection sont refusées. |

---

## 🛠️ Utiliser les scripts seuls

<details>
<summary>Voir les commandes</summary>

```bash
# 1. Inventaire
python scripts/organize.py inventory "<source>" --out inventory.json

# 2. Vérifier un plan
python scripts/organize.py plan-check plan.json --inventory inventory.json

# 3. Aperçu (dry-run), puis application
python scripts/organize.py apply plan.json
python scripts/organize.py apply plan.json --apply

# 4. Vérifier les liens dans la cible
python scripts/organize.py verify "<cible>"

# 5. Détection du projet et sécurité
python scripts/detect_project.py scan "<source>" --out design-inventory.json
python scripts/detect_project.py skills --require superpowers,security-audit
python scripts/security_check.py scan "<cible>" --out baseline.json
python scripts/security_check.py requirements --intent dashboard --inventory design-inventory.json

# 6. Préproduction multi-agents
python scripts/scaffold_memory.py "<cible>" --name "Mon projet" \
  --file-map "<cible>/docs/cleanup/file-map.json" --agents claude,codex [--private-memory]
```

Format du plan : [`references/plan-format.md`](references/plan-format.md). Tests : `npm test`.

</details>

## 📁 Contenu du dépôt

| Chemin | Rôle |
|---|---|
| [`SKILL.md`](SKILL.md) | Déroulé de la skill (étapes 0 à 9, garde-fous) |
| [`references/`](references/) | Conventions de dossiers, stacks par intention, réutilisation du design, sécurité, format du plan, prompts des sous-agents |
| [`scripts/organize.py`](scripts/organize.py) | Inventaire, vérification du plan, application, vérification des liens |
| [`scripts/detect_project.py`](scripts/detect_project.py) | Intention, écrans existants, contrat backend, skills compagnes |
| [`scripts/security_check.py`](scripts/security_check.py) | Candidats de sécurité, exigences par stack |
| [`scripts/scaffold_memory.py`](scripts/scaffold_memory.py) | Création de `.agents/` et des adaptateurs par agent, `--check`, `--update` |
| [`templates/agents/`](templates/agents/) | Protocole mémoire, règles du graphe, hook `memory_hook.py` |
| [`bin/cli.js`](bin/cli.js) | CLI npx : `install`, `run`, `scan`, `security`, `requirements`, `skills`, `init`, `doctor`… |
| [`install.sh`](install.sh) · [`install.ps1`](install.ps1) | Installation en une ligne, sans npm |
| [`tests/`](tests/) | Tests de bout en bout |

---

<div align="center">

Licence [MIT](LICENSE) · Fait pour Claude Code, Codex et tous les agents qui lisent `AGENTS.md`

</div>
