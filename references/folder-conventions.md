# Conventions d'arborescence

## Racine (presque tous les langages)

```
mon-projet/
├── README.md              # Obligatoire : la porte d'entrée
├── LICENSE                # Seulement si l'utilisateur la choisit
├── .gitignore
├── .env.example           # Variables d'environnement (jamais le vrai .env)
├── package.json / pyproject.toml / go.mod / …
├── AGENTS.md · CLAUDE.md  # Instructions agents, renvoient vers .agents/memory/
├── .agents/               # memory/, hooks/, graph/, skills/ (tous agents) ; .claude/ et .codex/ : hooks
├── src/ (ou app/)         # TOUT le code source
├── tests/                 # ou __tests__ / colocalisés
├── docs/                  # doc technique, architecture, ADRs
├── scripts/               # setup, migration, deploy
├── config/                # optionnel
├── public/ ou static/     # assets publics (front)
├── build/ ou dist/        # généré — jamais commité
└── tools/                 # outils internes (optionnel)
```

## Organisation de `src/`

**Par couches** (petits projets) : `controllers/ services/ models/ repositories/ middlewares/ utils/ config/`.

**Par features** (recommandé dès que ça grossit) :

```
src/
├── features/<domaine>/{components,hooks,services,types}/ + index.ts (API publique)
├── shared/ (ou common/) {ui,utils,types}/
└── app/                  # bootstrap, routing, providers
```

## Cible type pour un **export de design system** (cas par défaut)

```
<projet>/
├── README.md · AGENTS.md · CLAUDE.md · .gitignore
├── .agents/                   # mémoire partagée par tous les agents (créée par scaffold_memory.py)
│   ├── memory/                # protocole, état, journal, décisions, problèmes
│   ├── hooks/memory_hook.py
│   ├── graph/graph.json
│   └── skills/<ds>/SKILL.md   # la skill de l'outil de design, si fournie
├── .claude/                   # Claude Code : settings.json (hooks), skills/<ds> (copie)
├── .codex/hooks.json          # Codex : hooks
├── src/
│   ├── styles/
│   │   ├── index.css          # point d'entrée (@import des tokens + composants)
│   │   ├── tokens/            # colors.css, typography.css, spacing.css, effects.css, motion.css
│   │   └── components.css
│   ├── components/
│   │   └── <catégorie>/<Composant>/   # Button.jsx · Button.d.ts · Button.md (ex-.prompt.md)
│   ├── assets/
│   │   ├── brand/             # logos, wordmark, icône
│   │   └── images/            # images réellement utilisées par l'UI
│   └── mocks/                 # données factices (data.js…)
├── prototypes/                # écrans HTML/JSX de maquette, toujours lançables
│   └── <écran>/index.html
├── docs/
│   ├── design-system/
│   │   ├── README.md          # fondations : couleur, typo, forme, motion, ton, iconographie
│   │   ├── specimens/         # guidelines/*.html, *.card.html
│   │   └── references/        # captures d'inspiration conservées (sélection)
│   ├── adr/0001-structure-du-projet.md
│   └── cleanup/               # file-map.json + report.md (généré par apply)
└── vendor/                    # bundles générés indispensables aux prototypes (à régénérer plus tard)
```

Adapter si la stack est connue : Next.js → `src/app/` ; monorepo → `apps/web`, `packages/ui` (composants + tokens), `packages/config` ; Python → `app/` ; Go → `cmd/ internal/ pkg/`.

## Monorepo (front + back + partagé)

```
apps/{web,api,admin}/   packages/{ui,shared,config,database}/   pnpm-workspace.yaml | turbo.json | nx.json
```

## Selon l'intention (voir `stacks.md`)

| Intention | Racine cible | Les maquettes deviennent |
|---|---|---|
| Site vitrine | `site/` (Astro) [+ `api/`] | `site/src/pages/*.astro` |
| Dashboard | `web/` (SvelteKit/Next) + `api/` (Axum) | `web/src/routes/(auth)/…`, `(app)/…`, `(admin)/…` |
| Desktop | `app/src/` + `app/src-tauri/` | vues de `app/src/` |
| Mobile | `core/` (Rust UniFFI) + `ios/` + `android/` | vues SwiftUI / écrans Compose |
| Plusieurs | `apps/{site,web,desktop}/` + `api/` + `packages/ui/` | idem par app |

Toujours : `prototypes/` garde les maquettes d'origine (référence visuelle) tant qu'elles ne sont pas portées ; `docs/design/screens.md` fait le lien écran → route → endpoint ; `docs/security/` reçoit les exigences et rapports d'audit.

## Règles d'or

1. README clair d'abord (installer, lancer, tester, structure).
2. Un seul endroit pour le code source.
3. Tests séparés ou colocalisés, mais cohérents.
4. Aucun fichier généré dans git (dist, node_modules, __pycache__, .next…).
5. Noms courts, cohérents : dossiers en `kebab-case`, composants React en `PascalCase`, pas d'espaces, pas d'accents, pas de `final`, `v2`, `copy`, `(1)`.
6. Plus le projet grandit, plus on passe en feature-based.
7. Décisions d'architecture dans `docs/adr/` (une ADR par décision).
8. Un composant = un dossier qui contient tout ce qui le concerne (code, types, doc, story/test).
