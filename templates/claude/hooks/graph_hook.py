#!/usr/bin/env python3
"""Mémoire graphe du projet pour Claude Code.
Mode hook : lit l'événement JSON sur stdin.
Mode CLI  : graph_hook.py query <terme> | graph_hook.py note <sujet> <texte> | graph_hook.py index
"""
import ast
import json
import os
import re
import sys
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()
GDIR = ROOT / ".claude" / "graph"
GFILE = GDIR / "graph.json"
EVENTS = GDIR / "events.jsonl"
SECRET = re.compile(
    r"""(?i)((?:api[_-]?key|token|secret|password|passwd|pwd|authorization|credential)[\w-]*["']?\s*(?:[=:]|\s)\s*)"""
    r"""(?:bearer\s+|basic\s+)?("[^"]*"|'[^']*'|\S+)"""
)
SECRET_SHAPES = re.compile(
    r"(gh[pousr]_\w+|github_pat_\w+|sk-[\w-]{10,}|xox[abpr]-[\w-]+|AKIA\w{16}|AIza[\w-]{30,}|eyJ[\w-]+\.[\w-]+\.[\w-]+)"
)
URL_CREDS = re.compile(r"(//[^/\s:@]+):[^@\s/]+@")
IMPORT_RE = re.compile(
    r"""(?:from\s+['"](\.{1,2}/[^'"]+)['"]|import\s+['"](\.{1,2}/[^'"]+)['"]|require\(['"](\.{1,2}/[^'"]+)['"]\))"""
)
MARKUP_RE = re.compile(r"""(?:\b(?:src|href)\s*=\s*["']([^"'#?]+)|@import\s+(?:url\()?["']?([^"')\s;]+)|url\(\s*["']?([^"')#?]+))""")
JS_EXT = (".ts", ".tsx", ".js", ".jsx", ".mjs")
MARKUP_EXT = (".html", ".htm", ".css", ".scss", ".svg")
IGNORED = (".git/", "node_modules/", ".claude/graph/", "dist/", "build/", ".next/", "__pycache__/", ".venv/")


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def redact(s):
    s = SECRET.sub(r"\1<redacted>", s or "")
    s = SECRET_SHAPES.sub("<redacted>", s)
    return URL_CREDS.sub(r"\1:<redacted>@", s)


def load():
    if GFILE.exists():
        try:
            g = json.loads(GFILE.read_text(encoding="utf-8"))
            g["_seen"] = {(e["src"], e["rel"], e["dst"]) for e in g["edges"]}
            return g
        except (ValueError, OSError, KeyError, TypeError):
            # graphe corrompu : on le met de côté au lieu de bloquer chaque hook
            GFILE.replace(GFILE.with_name(f"graph.json.bad-{int(time.time())}"))
    return {"nodes": {}, "edges": [], "_seen": set()}


def save(g):
    GDIR.mkdir(parents=True, exist_ok=True)
    tmp = GDIR / f"graph.{os.getpid()}.tmp"
    data = {k: v for k, v in g.items() if k != "_seen"}
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    for attempt in range(5):  # Windows refuse le remplacement si un autre hook lit le fichier
        try:
            tmp.replace(GFILE)
            return
        except PermissionError:
            time.sleep(0.05 * (attempt + 1))
    tmp.unlink(missing_ok=True)


def node(g, nid, kind, **props):
    n = g["nodes"].setdefault(nid, {"kind": kind, "created": now()})
    n.update(props)
    n["updated"] = now()
    return nid


def edge(g, src, rel, dst):
    key = (src, rel, dst)
    if key not in g["_seen"]:
        g["_seen"].add(key)
        g["edges"].append({"src": src, "rel": rel, "dst": dst})


def to_rel(p):
    if not p:
        return None
    try:
        rel = Path(p).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return None
    return None if (rel + "/").startswith(IGNORED) or any(f"/{i}" in f"/{rel}" for i in IGNORED) else rel


def kind_of(rel):
    if rel.startswith(".claude/graph/"):
        return None
    if rel.startswith(".claude/agents/"):
        return "agent"
    if rel.startswith(".claude/skills/"):
        return "skill"
    if rel.startswith(".claude/commands/"):
        return "command"
    if rel.startswith(".claude/hooks/"):
        return "hook"
    if rel.startswith(".claude/memory/") or rel.endswith(("CLAUDE.md", "CLAUDE.local.md")):
        return "memory_doc"
    if rel.startswith(".claude/") and rel.endswith(".json"):
        return "config"
    return "file"


def _link(g, fid, target):
    tr = to_rel(str(target))
    if tr:
        k = kind_of(tr) or "file"
        edge(g, fid, "IMPORTS", node(g, f"{k}:{tr}", k, path=tr))


def link_imports(g, fid, rel):
    p = ROOT / rel
    if not p.is_file():
        return
    if p.suffix in JS_EXT:
        for m in IMPORT_RE.finditer(p.read_text(encoding="utf-8", errors="ignore")):
            target = next(x for x in m.groups() if x)
            for cand in (target, target + ".ts", target + ".tsx", target + ".js", target + ".jsx",
                         target + "/index.ts", target + "/index.tsx", target + "/index.js"):
                t = (p.parent / cand).resolve()
                if t.is_file():
                    _link(g, fid, t)
                    break
    elif p.suffix in MARKUP_EXT:
        for m in MARKUP_RE.finditer(p.read_text(encoding="utf-8", errors="ignore")):
            target = next(x for x in m.groups() if x)
            if re.match(r"^(?:[a-z]+:|//|data:)", target, re.I):
                continue
            base = ROOT if target.startswith("/") else p.parent
            t = (base / target.lstrip("/")).resolve()
            if t.is_file():
                _link(g, fid, t)
    elif p.suffix == ".py":
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="ignore"))
        except (SyntaxError, ValueError, RecursionError, MemoryError):
            return
        for n in ast.walk(tree):
            mods = []
            if isinstance(n, ast.Import):
                mods = [(a.name, 0) for a in n.names]
            elif isinstance(n, ast.ImportFrom) and n.module is not None:
                mods = [(n.module, n.level)]
            for mod, level in mods:
                base = p.parent
                for _ in range(max(level - 1, 0)):
                    base = base.parent
                base = base if level else ROOT
                stem = base.joinpath(*mod.split("."))
                for t in (stem.with_suffix(".py"), stem / "__init__.py"):
                    if t.is_file():
                        _link(g, fid, t)
                        break


def summary(g):
    kinds = {}
    for n in g["nodes"].values():
        kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
    counts = ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())) or "vide"
    py = "python" if os.name == "nt" else "python3"
    return (f"Mémoire graphe du projet ({counts}). Avant de modifier un fichier, lance "
            f"`{py} .claude/hooks/graph_hook.py query <chemin>` pour voir ses dépendances. "
            "Lire .claude/memory/etat.md avant d'agir.")


def index(g):
    count = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if to_rel(os.path.join(dirpath, d)) is not None]
        for f in filenames:
            rel = to_rel(os.path.join(dirpath, f))
            k = kind_of(rel) if rel else None
            if not k:
                continue
            fid = node(g, f"{k}:{rel}", k, path=rel)
            link_imports(g, fid, rel)
            count += 1
    save(g)
    print(f"ok — {count} fichiers indexés, {len(g['edges'])} arêtes")


def cli(args):
    g = load()
    if args[0] == "query" and len(args) >= 2:
        term = " ".join(args[1:]).lower().replace("\\", "/")
        hits = [n for n in g["nodes"] if term in n.lower()]
        if not hits:
            print("aucun résultat")
        for nid in hits:
            print(f"[{g['nodes'][nid]['kind']}] {nid}")
            for fact in g["nodes"][nid].get("facts", []):
                print(f"    fait: {fact}")
        for e in g["edges"]:
            if e["src"] in hits or e["dst"] in hits:
                print(f"  {e['src']} -[{e['rel']}]-> {e['dst']}")
    elif args[0] == "note" and len(args) >= 3:
        nid = node(g, f"concept:{args[1]}", "concept")
        g["nodes"][nid].setdefault("facts", []).append(f"{now()} {redact(' '.join(args[2:]))}")
        save(g)
        print("ok")
    elif args[0] == "index":
        index(g)
    else:
        print("usage: query <terme> | note <sujet> <texte> | index")


def hook(ev):
    name = ev.get("hook_event_name", "")
    sid = ev.get("session_id", "unknown")
    g = load()
    sess = node(g, f"session:{sid}", "session")
    log = {"t": now(), "event": name, "session": sid}

    if name == "SessionStart":
        save(g)
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                                 "additionalContext": summary(g)}}, ensure_ascii=False))
    elif name == "PostToolUse":
        tool, inp = ev.get("tool_name", ""), ev.get("tool_input", {}) or {}
        log["tool"] = tool
        if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
            rel = to_rel(inp.get("file_path") or inp.get("notebook_path"))
            k = kind_of(rel) if rel else None
            if k:
                fid = node(g, f"{k}:{rel}", k, path=rel)
                edge(g, sess, "TOUCHED", fid)
                link_imports(g, fid, rel)
                log["path"] = rel
        elif tool in ("Bash", "PowerShell"):
            log["cmd"] = redact(inp.get("command", ""))[:300]
        elif tool in ("Task", "Agent") and inp.get("subagent_type"):
            edge(g, sess, "INVOKED", node(g, f"agent:{inp['subagent_type']}", "agent"))
            log["agent"] = inp["subagent_type"]
        elif tool == "Skill" and inp.get("skill"):
            edge(g, sess, "INVOKED", node(g, f"skill:{inp['skill']}", "skill"))
            log["skill"] = inp["skill"]
        save(g)
    elif name in ("Stop", "SubagentStop", "PreCompact", "SessionEnd"):
        g["nodes"][sess]["last_event"] = name
        # nom seul : le chemin absolu contient le nom d'utilisateur et graph.json peut être versionné
        g["nodes"][sess]["transcript"] = Path(ev.get("transcript_path") or "").name or None
        save(g)

    GDIR.mkdir(parents=True, exist_ok=True)
    with EVENTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli(sys.argv[1:])
    else:
        try:
            hook(json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}"))
        except Exception as exc:  # un hook ne doit jamais bloquer la session
            print(f"graph_hook: {exc}", file=sys.stderr)
        sys.exit(0)
