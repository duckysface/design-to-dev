# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.6.0] - 2026-11-05

### Added — smart duplicates

- **New `dedupe` command** (`npx design-to-dev dedupe <folder>`): analyzes duplicate groups with the
  reference graph and proposes plan actions. Exact duplicates get a merge action
  (`delete` + `replaced_by` towards the most-referenced, cleanest-named copy) whose references are
  rewritten on `apply`; near-duplicates are flagged `review` and never auto-deleted.
- **Near-duplicate detection** in `inventory`: a normalized hash (comments and whitespace ignored,
  strings preserved) flags files that are the same content apart from comments/formatting, with a
  `similar_to` list.
- **New `plan-check` guards**: deleting a still-referenced duplicate without `replaced_by` is now an
  error; deleting a near-duplicate requires either `replaced_by` or an explicit `review`;
  `replaced_by` targets must exist and be kept.

### Changed — much stronger AI trace removal

`ai-traces clean` now removes automatically (was: only flagged), still under the per-file proof:

- **tracking attributes** `data-lov-id`, `data-lov-name`, `data-component-*` in HTML/JSX
  (never inside strings or comments);
- **injected scripts** (`cdn.gpteng.co/gptengineer.js`…);
- **badges** that link to the AI tool's domain with an "Edit with / Made with…" text
  (no nested content);
- **the component tagger**: `lovable-tagger` import lines, `componentTagger()` calls in plugin
  arrays (comma-aware), and its `package.json` entry — verified by JSON comparison
  (result must equal the original minus exactly the removed keys);
- **Markdown**: "This project was built with …" lines and whole boilerplate sections
  ("## Build with Lovable", "## Built with v0"…) up to the next same-level heading.
- The AI tool list now also covers Trae, Antigravity, Augment, Roo Code, Firebase Studio,
  Base44, create.xyz, Softgen, Tempo and Qodo.
- Functional dependencies (e.g. `@lovable.dev/mcp-js` actually imported by the code) are still
  never removed — only flagged.

### Documentation

- README is now English-first, with the full French version in `README.fr.md`.
- New `docs/commands.md` (full command reference + troubleshooting/FAQ), `CHANGELOG.md`,
  `CONTRIBUTING.md`, CI workflow, and an `examples/` walkthrough.
- Install docs no longer suggest piping a script into a shell: download, read, then run —
  matching the project's own pinning/hash-checking discipline.
- Badges (npm, CI, license, Python/Node requirements) and a CI usage example for
  `foundations --strict`.

### Fixed

- `scaffold_memory.py --check` no longer reports "a newer memory_hook.py is available" right after
  a fresh install on Windows: the comparison now normalizes line endings (LF), so a CRLF checkout
  (`core.autocrlf=true`) no longer causes a false positive. Added `.gitattributes` to enforce LF
  for scripts going forward.
- `ai_traces.py`: mentions of AI traces inside inline code (`` `…` ``) in Markdown are documentation,
  not traces — they are no longer flagged; boilerplate section detection no longer fires on headings
  about "design" in general (e.g. "### Claude Design / export …").

## [2.5.0] - 2026-10-30

### Added

- AI trace cleaner: visible signatures (comments, `<meta name="generator">`, Markdown footers,
  `Co-Authored-By`) and invisible Unicode watermarks, with a per-file proof the design is unchanged.
- Project security kit: pinned, scanned third-party security skills in `.claude/skills`.
- Dependency, runtime and API audit (`deps`, `--online`).

[2.6.0]: https://github.com/duckysface/design-to-dev/compare/v2.5.0...v2.6.0
[2.5.0]: https://github.com/duckysface/design-to-dev/releases/tag/v2.5.0
