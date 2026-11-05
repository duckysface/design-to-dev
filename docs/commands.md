# Command reference / Référence des commandes

The CLI is bilingual-agnostic: all commands work identically on Windows (`python`), macOS and Linux (`python3`). Python 3.9+ standard library only.

## CLI `npx design-to-dev`

| Command | What it does |
|---|---|
| `install` / `uninstall` | Installs or removes the skill (`--claude`, `--codex`, `--all`, `--project [dir]`, `-y`) |
| `--version` / `-v` | Prints the installed CLI version |
| `run <folder>` | Runs the agent on a folder (`--codex`, `--print`) |
| `init <folder>` | Installs only the memory on an existing project |
| `scan <folder>` | Intent, screens, backend contract, recommended stack |
| `inventory <folder>` | Raw file inventory (types, hashes, references, signals) |
| `dedupe <folder>` | Analyzes duplicate groups and proposes safe merges (`--out f.json`) |
| `foundations <folder>` | Verifies the base ✅ / ⚠️ / ❌ (`--strict` for CI) |
| `deps <folder>` | Dependency audit (`--online` for CVEs, stable versions, end-of-life) |
| `security <folder>` | Risk patterns (CWE + ASVS + fix hints) |
| `security-kit list\|install\|verify <folder>` | Pinned security skills kit in `.claude/skills` |
| `ai-traces scan\|clean <folder>` | Finds or removes AI traces (`--dry-run`, `--strict`, `--json`) |
| `requirements --intent dashboard` | Security checklist for the stack |
| `skills` | Are superpowers and security-audit installed? |
| `doctor` | Checks Python and installations |
| `path` | Folder of the installed skill |

### `init` options

```sh
npx design-to-dev init . --agents claude,codex,cursor
npx design-to-dev init . --next-step "Create the monorepo with apps/web"
npx design-to-dev init . --no-detect    # blank etat.md
npx design-to-dev init . --check        # verifies without writing
npx design-to-dev init . --update       # updates the hook
```

### `dedupe` — duplicate analysis

```sh
npx design-to-dev dedupe ./my-design                  # prints the analysis + actions JSON
npx design-to-dev dedupe ./my-design --out merge.json # writes plan actions to merge into plan.json
```

- Exact duplicate → `delete` + `replaced_by` (canonical = most-referenced, cleanest name); references are rewritten on `apply`.
- Near-duplicate (same content modulo comments/whitespace) → `keep` + `review`: decide together whether to merge or keep both variants.
- `plan-check` rejects deleting a referenced duplicate without `replaced_by`.

### `ai-traces` — AI trace removal

```sh
npx design-to-dev ai-traces scan <folder> [--strict] [--json]
npx design-to-dev ai-traces clean <folder> [--dry-run] [--out docs/cleanup/traces-ia.md] [--json]
```

Auto-removed (per-file proof): signature comments, AI `<meta name="generator">`, Markdown footers, "built with" lines, boilerplate sections, tracking attributes (`data-lov-id`, `data-component-*`), injected scripts, badges, the `lovable-tagger` plugin (import + calls + `package.json` entry), invisible watermarks. Only flagged: badges with nested content, content links (favicon, og:image, deploy URL), functional dependencies, traces inside code or strings.

## Memory commands

```sh
python .agents/hooks/memory_hook.py context                       # summary injected at startup
python .agents/hooks/memory_hook.py recall "bundler vite"         # search the memory
python .agents/hooks/memory_hook.py query src/styles/tokens.css   # who depends on this file
python .agents/hooks/memory_hook.py note tokens "source of truth for colors"
python .agents/hooks/memory_hook.py doctor                        # consistency, secrets, origin
python .agents/hooks/memory_hook.py archive                       # archives old entries
```

## Raw Python scripts, without an agent

```sh
# Cleanup
python scripts/organize.py inventory "<source>" --out inventory.json
python scripts/organize.py dedupe "<source>" --out merge-actions.json
python scripts/organize.py plan-check plan.json --inventory inventory.json
python scripts/organize.py apply plan.json            # preview
python scripts/organize.py apply plan.json --apply    # apply
python scripts/organize.py verify "<target>"

# Detection and security
python scripts/detect_project.py scan "<source>" --out design-inventory.json
python scripts/security_check.py foundations "<target>" --strict
python scripts/security_check.py scan "<target>" --out baseline.json
python scripts/security_check.py requirements --intent dashboard

# Pre-production memory
python scripts/preprod_log.py journal --dir "$M" --step 3 --agent claude-code "target tree approved"
python scripts/scaffold_memory.py "<target>" --agents claude,codex --import-preprod "$M"
python scripts/scaffold_memory.py "<target>" --check
```

Plan format: `references/plan-format.md`. Tests: `npm test`.

## Repository layout

| Path | Role |
|---|---|
| `SKILL.md` | The skill's runbook (steps 0 to 9) |
| `references/` | Conventions, stacks, security, plan format, sub-agent prompts |
| `scripts/organize.py` | Inventory, dedupe, plan check, copy, link verification |
| `scripts/detect_project.py` | Intent, screens, backend contract, companion skills |
| `scripts/security_check.py` · `scripts/foundations.py` | Foundations, risk patterns, requirements |
| `scripts/deps_audit.py` | Dependency, runtime and API audit |
| `scripts/ai_traces.py` | AI trace scanner and cleaner |
| `scripts/security_kit.py` | Pinned security skills kit |
| `scripts/preprod_log.py` | Memory filled live during pre-production |
| `scripts/scaffold_memory.py` | Creates `.agents/` and per-agent adapters |
| `templates/agents/` | Memory protocol and `memory_hook.py` hook |
| `bin/cli.js` | npx CLI |
| `install.sh` · `install.ps1` | npm-free installation |
| `tests/` | End-to-end tests |

## Troubleshooting / FAQ

**`doctor` says Python is missing.**
Install Python 3.9+ and make sure `python` (Windows) or `python3` (macOS/Linux) is in your PATH. No pip packages are needed — the skill is stdlib-only.

**`plan-check` fails with "deletion of a file still in use".**
A file you marked `delete` is referenced by a file you keep. Either keep it, or set `replaced_by` to the file that takes over — references will be rewritten automatically. Run `dedupe` to get ready-made merge actions.

**`plan-check` fails with "near-duplicate deleted without merge or review".**
That's intentional: two similar variants may serve different screens. Decide with the user: merge (`delete` + `replaced_by`) or keep both (`keep`, drop the `review` flag after the decision).

**`apply --apply` refuses the plan: "items still marked review".**
Every `review: true` is an explicit question for the user. Resolve each one (change the action or remove the flag) before applying.

**`ai-traces clean` left a file untouched with a ❌ "proof failed".**
The proof found a difference beyond AI traces. The file was not modified. Open the report (`docs/cleanup/traces-ia.md`), inspect that file, and remove the trace manually — the proof exists precisely for files like this.

**Something is still flagged after `ai-traces clean`.**
That's the "⚠️ to verify" section: content links (deployment URLs, og:image), functional dependencies (`@lovable.dev/*` actually imported), badges with nested content, and traces inside code or strings are never auto-removed. Review them one by one.

**A Lovable/Bolt export has `@lovable.dev/*` packages in package.json — are they removed?**
No. Only `lovable-tagger` (a pure dev-time marker) is removed. Packages your code actually imports are functional dependencies and are only flagged.

**The skill didn't detect the right intent.**
Run `npx design-to-dev scan <folder>` and read the `intent.scores`. You can force the stack with a profile (`DESIGN_TO_DEV_STACK=path/to/stack.json`) — see `references/stacks.md`.

**`--check` on `init` reports missing journal entries.**
The memory expects one journal entry per step 0–9. Skipped steps (quick mode) must be logged too, with title `(ignored — quick mode)`.

**Where are the installed files?**
`npx design-to-dev path` prints the installed skill folder; `npx design-to-dev doctor` checks everything.
