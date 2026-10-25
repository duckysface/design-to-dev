# Règles de classification : garder, déplacer, supprimer

Chaque fichier reçoit une action : `keep` (même chemin), `move` (nouveau chemin `dst`), `delete` (non copié dans la cible). Toujours une `reason` courte et vérifiable.

## Principes

1. **Référencé = vivant.** Un fichier référencé par un fichier conservé ne se supprime pas (sauf `replaced_by`). Vérifier `inbound` dans `inventory.json`.
2. **Orphelin ≠ inutile.** Un orphelin peut être une source (logo SVG d'origine, doc). Le juger sur son contenu.
3. **Généré = régénérable.** Un artefact généré se supprime s'il n'est utilisé par rien de conservé ; sinon il va dans `vendor/` avec une note « à régénérer ».
4. **Doute → `review`.** Mieux vaut une question à l'utilisateur qu'une perte.
5. **Données personnelles → `review` toujours** (photos de personnes réelles, captures de conversations, emails, noms de clients).

## Toujours supprimer (sauf contre-indication)

| Motif | Exemples |
|---|---|
| Déchets OS | `.DS_Store`, `Thumbs.db`, `desktop.ini`, `__MACOSX/`, `._*`, `*.tmp`, `~$*` |
| Dépendances / builds | `node_modules/`, `dist/`, `build/`, `.next/`, `.nuxt/`, `.turbo/`, `.cache/`, `__pycache__/`, `*.pyc`, `coverage/` |
| Logs | `*.log`, `npm-debug.log*`, `yarn-error.log` |
| Copies / backups | `* copy.*`, `*(1).*`, `*-old.*`, `*.bak`, `*.orig`, `*_backup*`, `final-final*` — si l'original existe |
| Doublons exacts | même hash : garder un exemplaire canonique |
| Vignettes d'outil | `.thumbnail`, `thumbnail.html`, `thumbnail.png` générés par l'outil d'export |
| Secrets | `.env` réel → ne PAS copier, créer `.env.example` avec les noms de variables seulement |

## Artefacts d'outils de design connus

### Claude Design / export « design system » de claude.ai
| Fichier | Décision par défaut |
|---|---|
| `SKILL.md` racine (skill de marque) | `move` → `.agents/skills/<ds>/SKILL.md` (recopiée dans `.claude/skills/` pour Claude Code) (corriger les chemins vers `docs/design-system/README.md`) |
| `readme.md` | `move` → `docs/design-system/README.md` (et s'en servir pour le README racine) |
| `styles.css` (point d'entrée `@import`) | `move` → `src/styles/index.css` |
| `tokens/*.css` | `move` → `src/styles/tokens/` |
| `components/components.css` | `move` → `src/styles/components.css` |
| `components/<cat>/<X>.jsx` + `<X>.d.ts` | `move` → `src/components/<cat>/<X>/` |
| `components/<cat>/<X>.prompt.md` | `move` → `src/components/<cat>/<X>/<X>.md` (doc d'usage) |
| `components/<cat>/<cat>.card.html`, `guidelines/*.html` | `move` → `docs/design-system/specimens/` |
| `ui_kits/<écran>/` | `move` → `prototypes/<écran>/` (écrans de maquette, pas du code de prod) |
| `ui_kits/**/data.js` | `move` → `src/mocks/` si partagé, sinon reste avec son prototype |
| `_ds_bundle.js` | généré (bundle de tous les composants). Si des prototypes l'utilisent → `move` → `vendor/ds-bundle.js` ; sinon `delete` |
| `_ds_manifest.json` | métadonnées d'export → `delete` (sauf si un fichier conservé le lit) |
| `_adherence.oxlintrc.json` | règles lint d'adhérence au DS → `move` → `config/oxlintrc.adherence.json` si l'équipe veut l'utiliser, sinon `delete` ; en `review` par défaut |
| `uploads/pasted-*.png`, `uploads/<hash>.jpg` | captures d'inspiration : non référencées → sélectionner les plus utiles vers `docs/design-system/references/` (renommées lisiblement), le reste `delete` ; en cas de doute `review` |
| `uploads/*` photo de personne | `review` (donnée personnelle) |

### Figma / Sketch / Penpot
`*.fig`, `*.sketch`, `*.penpot` → `design/` (source de vérité visuelle, ne pas supprimer). Exports `@2x/@3x` en double → garder la meilleure résolution ou celle utilisée.

### v0 / Lovable / Bolt / Replit / Cursor
`.bolt/`, `.lovable/`, `.replit`, `replit.nix`, `.vercel/`, `.netlify/` → `delete` (config d'hébergement de l'outil) sauf si l'utilisateur déploie avec. `components.json` (shadcn) → `keep`. `bun.lockb` + `package-lock.json` en même temps → garder celui du gestionnaire choisi, `review`.

### Projets faits main
Noms `final`, `v2`, `new`, `test`, `untitled`, `sans titre` → renommer selon le contenu ; comparer les versions, garder la plus récente/complète, l'autre `delete` avec `replaced_by` ou `review`.

## Renommage

- Dossiers : `kebab-case`, sans espaces ni accents (`UI Kits` → `prototypes`, `ui_kits` → `prototypes`).
- Composants : `PascalCase` cohérent entre `.jsx`, `.d.ts`, `.md`.
- Images de référence : `<sujet>-<nn>.png` (ex. `store-home-01.png`) plutôt que `pasted-1792872458499-0.png`.
- Garder les extensions et les noms de fichiers référencés par du code tiers (CDN, configs).

## Taille et confiance

- `confidence` : 0.9+ = évident (déchet OS, tokens) ; 0.7–0.9 = probable ; < 0.7 = `review: true`.
- Signaler tout fichier > 1 Mo et tout dossier > 50 % du poids total.
