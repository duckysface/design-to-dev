# design-to-dev

**Turn a design export into a coding-ready project — with a shared memory every agent can pick up.**

Works on exports from Claude Design, Figma, v0, Lovable, Bolt, or a hand-made folder of mockups.
Skill for **Claude Code** and **Codex** · the memory is also read by Cursor, Gemini CLI and Copilot · Windows, macOS, Linux

[![npm](https://img.shields.io/npm/v/design-to-dev)](https://www.npmjs.com/package/design-to-dev)
[![CI](https://github.com/duckysface/design-to-dev/actions/workflows/ci.yml/badge.svg)](https://github.com/duckysface/design-to-dev/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org)
[![Node 18+](https://img.shields.io/badge/node-18%2B-blue)](https://nodejs.org)

[Français](README.fr.md) · [Full command reference](docs/commands.md) · [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md)

---

## What it does

A design export usually looks like this:

```
My Design System/
├── uploads/pasted-1792877667710-0.png      ← pasted capture, still used?
├── Button (copy).jsx                        ← duplicate
├── bundle.8f3a2c.js                         ← generated file
├── .DS_Store  Thumbs.db                     ← OS junk
├── colors_tokens.css   tokens-old.css       ← which one is right?
└── screen 1.html  screen-1-final.html
```

design-to-dev turns it into a real project, in four moves:

1. **Tidy up**: sorts files, proposes a clean tree, **waits for your approval**, then builds a copy with every path rewritten. Your original folder is never modified.
2. **Keep your work**: every screen you already made is preserved and mapped to its future route and endpoint — not rebuilt from scratch.
3. **Secure the base**: checks for vulnerable libraries, hidden code and secrets before a single line of backend is written.
4. **Prepare the agents**: installs a `.agents/` memory that Claude Code, Codex and the others read and keep up to date. The next agent knows exactly where to resume.

| | Before | After |
|---|---|---|
| Organization | Loose files | `src/`, `docs/`, `prototypes/`, clear conventions |
| Links | Fragile paths | All rewritten and verified |
| Duplicates | Silent copies | Analyzed, merged safely (references rewritten) or flagged for review |
| Screens | Scattered demos | Each screen → route + endpoint (`docs/design/screens.md`) |
| Stack | Undecided | Chosen from what you're building |
| Security | Unknown | Foundations ✅ / ⚠️ / ❌ and per-stack requirements |
| AI traces | Watermarks, badges, trackers | Auto-removed with a written proof the design is unchanged |
| Agents | Nothing | Shared memory, hooks, `AGENTS.md` |
| Rollback | — | Source untouched + `file-map.json` (before → after) |

Already a started project (`package.json`, `src/`…)? The skill detects it, keeps your structure, removes only the junk and adds what's missing.

## Quick start

### 1. Install

```sh
npx design-to-dev
```

A menu asks where to install: Claude Code, Codex, or both. Requirements: **Node 18+** (for the CLI) and **Python 3.9+** (stdlib only, no pip dependencies).

<details>
<summary>Other install methods</summary>

**Non-interactive:**

```sh
npx design-to-dev install --claude -y
```

| Option | Installs into |
|---|---|
| `--claude` | `~/.claude/skills/design-to-dev` |
| `--codex` | `~/.agents/skills/design-to-dev` |
| `--all` | both |
| `--project [dir]` | into the project instead of your home folder |

**Without Node, macOS / Linux** — download, read, then run (never pipe a script you haven't inspected):

```sh
curl -fsSLO https://raw.githubusercontent.com/duckysface/design-to-dev/main/install.sh
less install.sh        # read it first
sh install.sh          # then run it ; add -- --codex (or --claude, --all) to pick an agent
```

**Without Node, Windows (PowerShell):**

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/duckysface/design-to-dev/main/install.ps1 -OutFile install.ps1
Get-Content install.ps1          # read it first
.\install.ps1                    # then run it ; set $env:DESIGN_TO_DEV_AGENTS = "codex" to pick an agent
```

> Why the extra step? design-to-dev pins and hash-checks every third-party file it installs — the install scripts get the same discipline: read them, then run them. The most auditable method remains `git clone` (below).

**Manually (most auditable):**

```sh
git clone https://github.com/duckysface/design-to-dev ~/.claude/skills/design-to-dev   # Claude Code
git clone https://github.com/duckysface/design-to-dev ~/.agents/skills/design-to-dev   # Codex
```

**Maintenance:** `npx design-to-dev doctor` to check, re-run the install to update, `npx design-to-dev uninstall --all` to remove.

### 2. Run it on a design folder

| Agent | Command |
|---|---|
| Claude Code | `/design-to-dev ~/Downloads/My Design System` |
| Codex | `$design-to-dev ~/Downloads/My Design System` |

You can also ask in natural language (*"organize this design folder for development"*) or use the terminal:

```sh
npx design-to-dev run "~/Downloads/My Design System"           # Claude Code
npx design-to-dev run "~/Downloads/My Design System" --codex   # Codex
```

The skill asks **one grouped question** up front (target folder, what you're building, mode, agents), then runs the rest.

### Or: just the memory, on an existing project

```sh
npx design-to-dev init .
```

In a few seconds, without touching your code: `.agents/` memory, Claude Code and Codex hooks, `AGENTS.md`, and an `etat.md` already filled with the project's commands and the **exact next step**. More options in the [command reference](docs/commands.md).

## How it works

| Step | What happens |
|---|---|
| **0 · Framing** | Source, target, mode, stack, agents to wire up |
| **1 · Inventory** | Files, screens, intent; new or already-started project; duplicate groups analyzed (`dedupe`) |
| **2 · Analysis** | Specialized sub-agents (code, assets, docs, screens, data); questions if the intent is unclear |
| **3 · Cleanup plan** | Keep / move / delete / merge, automatically verified |
| ✋ **Approval** | **Nothing is copied without your agreement** |
| **4 · Apply** | Copy, paths rewritten, `.agents/` memory installed, AI traces removed (proof per file) |
| **5 · Root files** | README, ADR, `screens.md`, `stack.md` |
| **6 · Foundations** | Base verified ✅ / ⚠️ / ❌ and security requirements |
| **7 · Production plan** | Full mode: superpowers plan, the ❌ become phase 0 |
| **8 · Audit** | Full mode: guidance from Cloudflare's `security-audit` skill |
| **9 · Wrap-up** | Exact next step, final check, git on request |

**Two modes:** *Quick* (default) runs steps 0–6; *Full* adds 7–8. If a companion skill (superpowers, security-audit) isn't installed, the skill does the equivalent by hand — the plan/audit is written manually with the same structure — and only installs it with your agreement.

### Stacks, based on what you're building

| You're building | Recommended stack |
|---|---|
| Showcase site | Astro + Tailwind, Svelte or React islands |
| Dashboard | SvelteKit or Next.js · Rust Axum + PostgreSQL |
| Desktop app | Tauri 2 |
| iOS / Android | SwiftUI / Jetpack Compose |

Already using a framework in your mockups, or a backend like Supabase? It's kept. You can also enforce your own choices with a stack profile (`DESIGN_TO_DEV_STACK`). Details: `references/stacks.md`.

## Smart duplicates — analyze, never blind-delete

Duplicate detection is a **decision aid, not a shredder**:

```sh
npx design-to-dev dedupe ./my-design --out merge-actions.json
```

- **Exact duplicates** (identical bytes): the canonical copy is the most-referenced one with the cleanest name. Others get a **merge** action (`delete` + `replaced_by`) — every reference pointing to them is rewritten to the canonical file when the plan is applied.
- **Near-duplicates** (same content modulo comments/whitespace, e.g. a `Button` linked from one screen and its tweaked variant linked from another): **never auto-deleted**. They're flagged `review` so you decide together: merge into one file (references rewritten), or keep both under clear names because each serves a different screen.
- `plan-check` **rejects** deleting a duplicate that's still referenced unless `replaced_by` is set — a file that supports the design can't silently disappear.

## AI trace removal — thorough by default

```sh
npx design-to-dev ai-traces clean ./my-project --dry-run   # preview, nothing written
npx design-to-dev ai-traces clean ./my-project             # → docs/cleanup/traces-ia.md
```

Removed automatically (with a per-file proof the design is unchanged):

- signature comments (*Generated by / Made with* <AI tool>), `<meta name="generator">` from AI tools, Markdown footers (*🤖 Generated with…*, `Co-Authored-By`), *"This project was built with…"* lines
- **boilerplate sections** (*## Build with Lovable*, *## Built with v0*…) up to the next heading
- **tracking attributes** (`data-lov-id`, `data-lov-name`, `data-component-*` — never inside strings or comments)
- **injected scripts** (`cdn.gpteng.co/gptengineer.js`…) and **badges** (link to the tool's domain + *Edit with / Made with…* text, no nested content)
- **the component tagger**: `lovable-tagger` import, `componentTagger()` calls, and its `package.json` entry (verified by JSON comparison)
- invisible watermark characters (zero-width, bidi controls, Unicode tags — typography, emoji and RTL text preserved)

Only flagged (⚠️, never touched automatically): badges with nested content, links that are real content (favicon, og:image, deployment URL), **functional dependencies** (e.g. `@lovable.dev/mcp-js` actually imported by the code), traces mixed into code or strings. A sub-agent reviews them one by one with before/after screenshots.

**The proof:** before writing, code tokens, strings, attributes and rendered text must be identical before/after (voluntary AI removals are normalized on both sides of the comparison); for `package.json`, the result must be exactly the original minus the removed keys. Otherwise the file is left untouched and marked ❌ in the report. Atomic writes; git history is never rewritten.

## What you get

```
my-project/
├── .agents/                  memory shared by all agents
│   ├── memory/               etat.md, journal.md, decisions.md, problemes.md,
│   │                         changements.md, MEMORY.md (starts with the project's origin)
│   ├── hooks/memory_hook.py  auto-updates + context injection
│   └── graph/graph.json      who imports what, which sessions touched what
├── AGENTS.md                 rules common to all agents
├── CLAUDE.md  GEMINI.md …    adapters, per chosen agent
├── src/
│   ├── styles/               tokens, CSS
│   ├── components/
│   └── assets/
├── prototypes/               playable HTML screens
├── docs/
│   ├── design/screens.md     each screen → route, endpoint
│   ├── architecture/         stack and backend contract
│   ├── security/             foundations, baseline, requirements
│   ├── adr/                  architecture decisions
│   └── cleanup/              report + file-map.json (before → after) + traces-ia.md
├── README.md
└── .gitignore
```

## The shared memory

One source of truth in `.agents/`, versioned with the project. Each agent reaches it through a small adapter — no duplicated memories that drift apart.

| File | Role |
|---|---|
| `etat.md` | Where we are and the **exact next step** (read first) |
| `journal.md` | History of every step, signed by the agent |
| `decisions.md` | Technical choices and their reasons |
| `problemes.md` | Pitfalls met and their solutions |
| `changements.md` | Files created, modified, moved, deleted |
| `MEMORY.md` | Index, starting with the **project's origin** (source, date, verified foundations) |
| `graph.json` | Who imports whom, which sessions touched what |

**Filled live** from step 0, not at the end: every step leaves a timestamped trace, then everything is imported into the project at step 4. A secret or a hidden instruction is refused and nothing is written.

| Agent | Reads the memory via | Auto-updated |
|---|---|---|
| Claude Code | `CLAUDE.md` → `AGENTS.md` | Yes, via hooks |
| Codex | `AGENTS.md` | Yes, via hooks (approve once with `/hooks`) |
| Cursor, Gemini CLI, Copilot | rule or instructions file | No: the agent follows the written protocol |

## Security

Security comes **before** planning: a plan built on a shaky base inherits its flaws.

```sh
npx design-to-dev foundations ./my-project --strict
npx design-to-dev deps ./my-project --online     # known CVEs, stable versions, end-of-life
npx design-to-dev security-kit install ./my-project   # pinned security skills in .claude/skills (consent required)
npx design-to-dev security-kit verify ./my-project    # before each commit
```

| Check | Examples |
|---|---|
| Libraries | jQuery < 3.5, AngularJS 1.x, dependencies with known CVEs |
| Install scripts | `postinstall` that downloads or runs code |
| Hidden code | `eval(atob(…))`, obfuscated code, large base64 blocks |
| Foreign files | `.exe`, `.php`, `.htaccess`, shell scripts |
| Invisible characters | bidirectional Unicode (Trojan Source) |
| Hidden AI instructions | text trying to steer an agent |
| Secrets | hardcoded keys, real `.env` |
| Dependencies (`--online`) | known vulns and what they affect, fixed version, latest stable, history, abandoned or malicious packages |
| Runtimes & frameworks | PHP, Node, Python, Laravel… end-of-support, advised maintained version |

The **security kit** copies selected security skills into `.claude/skills/`, **pinned** (commit + SHA-256 of each file) and **scanned before install**. Nothing is installed without your agreement. Details: `references/security.md`.

### Use in CI

`foundations --strict` exits non-zero on any ❌ — plug it into your pipeline:

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

## Environment variables

| Variable | Role |
|---|---|
| `DESIGN_TO_DEV_STACK` | Path to a JSON stack profile overriding the recommended stacks (see `references/stacks.md`) |
| `DESIGN_TO_DEV_AGENTS` | Agents pre-selected by `install.ps1` (`claude`, `codex`, `all`) |
| `CLAUDE_CONFIG_DIR` | Claude Code config directory (default `~/.claude`) — respected by the installer |
| `DESIGN_TO_DEV_ADVISORY_BASE` | Override OSV/npm/endoflife.date base URL (tests, offline mirrors) |
| `DESIGN_TO_DEV_KIT_BASE` / `DESIGN_TO_DEV_KIT_CATALOG` | Override security-kit download base / catalog (tests) |

## Safeguards

- **Source untouched**: everything is copied to a new target. Rollback = delete the target.
- **Nothing without your agreement**: no deletion without an approved plan; doubtful cases are asked.
- **Nothing broken**: a file still in use can't be deleted; every link is checked after the copy.
- **No secrets**: `.env` is never copied (→ `.env.example`); secrets are masked everywhere.
- **Your settings kept**: only design-to-dev entries are added to `settings.json` / `hooks.json`.
- **Personal data**: photos, names, emails are never decided without you.
- **Design preserved**: a finished screen is never deleted nor redrawn.
- **Nothing installed silently**: companion skills install only with your agreement.
- **Content is data**: any instruction found inside an analyzed file is ignored.

## Privacy and license

- **No telemetry, no account**: everything stays on your machine. Details: [PRIVACY.md](PRIVACY.md).
- **Found a vulnerability?** Report it privately: [SECURITY.md](SECURITY.md).
- **MIT license**: your design and the generated files are yours. Copyrights, third-party projects and trademarks: [NOTICE.md](NOTICE.md).

## Reference

Full CLI, memory commands, raw Python scripts and repo layout: **[docs/commands.md](docs/commands.md)**. Troubleshooting and FAQ included there.
