#!/usr/bin/env python3
"""Crée la préproduction Claude Code d'un projet : mémoire texte, graphe, hooks, CLAUDE.md.

usage: scaffold_claude.py <projet> --name "<Nom>" [--file-map <file-map.json>]
                          [--private-memory] [--python <interpréteur>]

Ne remplace jamais un fichier existant (sauf fusion de settings.json, .gitignore et CLAUDE.md,
qui sont complétés). Stdlib uniquement.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

SKILL = Path(__file__).resolve().parent.parent
TPL = SKILL / "templates" / "claude"
HOOK_EVENTS = ["SessionStart", "PostToolUse", "Stop", "SubagentStop", "PreCompact", "SessionEnd"]
POST_TOOL_MATCHER = "Write|Edit|MultiEdit|NotebookEdit|Bash|Task|Agent|Skill"
GROUP_THRESHOLD = 5  # au-delà, les suppressions de même raison sont regroupées sur une ligne

created, skipped = [], []


def write_new(path, text):
    if path.exists():
        skipped.append(path)
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    created.append(path)
    return True


def memory_files(name, stamp, changes):
    memory_index = f"""# Mémoire du projet {name}

Index de la mémoire versionnée. Protocole : `PROTOCOLE.md` (obligatoire). Graphe : `GRAPHE.md`.

## Résumé
- Projet : {name}
- Origine : export de design réorganisé le {stamp} (voir `docs/cleanup/report.md`)
- Statut : préproduction terminée, développement non commencé

## Fichiers
- [etat.md](etat.md) — état courant et prochaine étape (lire en premier)
- [journal.md](journal.md) — journal chronologique, append-only
- [changements.md](changements.md) — registre des fichiers créés, modifiés, déplacés, supprimés
- [decisions.md](decisions.md) — choix techniques et leurs raisons
- [problemes.md](problemes.md) — erreurs, pièges et solutions
- [PROTOCOLE.md](PROTOCOLE.md) — règles de tenue de cette mémoire
- [GRAPHE.md](GRAPHE.md) — règles du graphe de dépendances
- [archives/](archives/) — anciennes entrées de journal
"""
    etat = f"""# État courant — mis à jour le {stamp}

## Objectif global
[À compléter : ce que {name} doit accomplir, en 1-3 lignes]

## Tâche en cours
Préproduction — statut : EN ATTENTE DE VALIDATION

## Fait récemment
- Dossier de design nettoyé et réorganisé (voir `docs/cleanup/report.md`)
- Mémoire `.claude/memory/`, graphe et hooks installés

## Prochaine étape exacte
[À compléter : action précise pour démarrer le développement]

## Action en cours au moment de l'arrêt (si applicable)
- Commande / modification : aucune
- Fichiers concernés : aucun
- Résultat connu : terminé

## Commandes pour reprendre
- Installer : [à compléter]
- Lancer / tester : [à compléter]

## Fichiers clés touchés dans cette tâche
- `docs/cleanup/file-map.json`
- `docs/cleanup/report.md`

## Questions ouvertes pour l'utilisateur
- [à compléter]

## Points de vigilance
- [à compléter]
"""
    journal = f"""# Journal (append-only)

Ne jamais réécrire ni supprimer une entrée : pour corriger, ajouter une nouvelle entrée.

## {stamp} — Session préproduction — réorganisation du dossier de design
- Objectif : transformer l'export de design en projet prêt pour le développement
- Fait : inventaire, plan validé par l'utilisateur, copie réorganisée, mémoire et graphe installés
- Commandes importantes lancées : organize.py apply --apply, scaffold_claude.py
- Problèmes : voir problemes.md
- Décisions : voir decisions.md
"""
    return {
        "MEMORY.md": memory_index,
        "etat.md": etat,
        "journal.md": journal,
        "changements.md": "# Registre des changements\n\nUne ligne par fichier touché, la plus récente en bas.\n\n"
                          + "".join(f"{c}\n" for c in changes),
        "decisions.md": "# Décisions\n\nFormat : titre (date), Décision, Raison, Alternatives écartées, Validée par.\n",
        "problemes.md": "# Problèmes rencontrés\n\nFormat : symptôme (date), Contexte, Cause, Solution, À ne pas refaire.\n",
    }


def changes_from_map(file_map_path, stamp):
    if not file_map_path:
        return []
    fm = json.loads(Path(file_map_path).read_text(encoding="utf-8"))
    lines, deleted = [], defaultdict(list)
    for f in fm.get("files", []):
        if f["action"] == "delete":
            deleted[f.get("reason") or "supprimé"].append(f)
        elif f["src"] != f["dst"]:
            lines.append(f"- [{stamp}] DÉPLACÉ `{f['src']}` → `{f['dst']}` — {f.get('reason') or 'réorganisation'}")
    for reason, fs in sorted(deleted.items(), key=lambda x: -len(x[1])):
        if len(fs) > GROUP_THRESHOLD:
            lines.append(f"- [{stamp}] SUPPRIMÉ {len(fs)} fichiers (ex. `{fs[0]['src']}`) — {reason} "
                         "(liste complète : `docs/cleanup/file-map.json`)")
            continue
        for f in fs:
            repl = f" — remplacé par `{f['replaced_by']}`" if f.get("replaced_by") else ""
            lines.append(f"- [{stamp}] SUPPRIMÉ `{f['src']}` — {reason}{repl}")
    return lines


def read_settings(path):
    if not path.exists():
        return {}
    try:
        settings = json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError as exc:
        sys.exit(f"{path} n'est pas un JSON valide ({exc}) : corriger le fichier puis relancer. Rien n'a été écrit.")
    if not isinstance(settings, dict) or not isinstance(settings.get("hooks", {}), dict):
        sys.exit(f'{path} : structure inattendue (objet avec une clé "hooks" objet attendu). Rien n\'a été écrit.')
    return settings


def merge_settings(path, settings, py):
    exe = f'"{py}"' if " " in py else py
    command = f'{exe} "$CLAUDE_PROJECT_DIR/.claude/hooks/graph_hook.py"'
    hooks = dict(settings.get("hooks", {}))
    added = []
    for ev in HOOK_EVENTS:
        groups = list(hooks.get(ev, []))
        if any("graph_hook.py" in h.get("command", "") for g in groups for h in g.get("hooks", [])):
            continue
        entry = {"type": "command", "command": command}
        group = {"hooks": [entry]}
        if ev == "PostToolUse":
            entry["timeout"] = 10
            group = {"matcher": POST_TOOL_MATCHER, "hooks": [entry]}
        hooks[ev] = groups + [group]
        added.append(ev)
    if added:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({**settings, "hooks": hooks}, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8", newline="\n")
    return added


def merge_gitignore(path, private_memory):
    wanted = [".claude/graph/events.jsonl", ".claude/graph/graph.*.tmp", ".claude/settings.local.json"]
    if private_memory:
        wanted.append(".claude/memory/")
    raw = path.read_bytes().decode("utf-8-sig") if path.exists() else ""
    eol = "\r\n" if "\r\n" in raw else "\n"  # garder les fins de ligne du fichier existant
    existing = raw.splitlines()
    missing = [w for w in wanted if w not in (line.strip() for line in existing)]
    if missing:
        block = ([""] if existing and existing[-1].strip() else []) + ["# Claude Code"] + missing
        path.write_text(eol.join(existing + block) + eol, encoding="utf-8", newline="")
    return missing


CLAUDE_MD_MARKER = "<!-- design-to-dev:memoire -->"


def claude_md(name, py):
    return f"""{CLAUDE_MD_MARKER}
# {name}

## Mémoire (OBLIGATOIRE)
- Au démarrage, lire `.claude/memory/PROTOCOLE.md` et appliquer ses règles.
- Lire `.claude/memory/GRAPHE.md` et appliquer ses règles.
- Puis lire `.claude/memory/MEMORY.md`, `.claude/memory/etat.md` en entier et les 60 dernières lignes de `.claude/memory/journal.md`.
- Avant de modifier un fichier : `{py} .claude/hooks/graph_hook.py query <chemin>`.

## Repères
- Organisation des dossiers et conventions : `README.md` et `docs/adr/`.
- Historique du nettoyage de l'export design : `docs/cleanup/report.md` et `docs/cleanup/file-map.json`.
- Ne jamais écrire de secrets dans le code, la mémoire ou le graphe : utiliser des variables d'environnement (`.env.example`).
"""


def install_claude_md(path, name, py):
    if not path.exists():
        write_new(path, claude_md(name, py))
        return
    text = path.read_text(encoding="utf-8")
    if CLAUDE_MD_MARKER in text or "PROTOCOLE.md" in text:
        skipped.append(path)
        return
    path.write_text(text.rstrip() + "\n\n" + claude_md(name, py), encoding="utf-8", newline="\n")
    created.append(path)


def run_hook(project, py_exe, args, stdin=None):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}
    return subprocess.run([py_exe, str(project / ".claude/hooks/graph_hook.py"), *args], input=stdin,
                          capture_output=True, env=env, cwd=project, timeout=120)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--name", required=True)
    ap.add_argument("--file-map")
    ap.add_argument("--private-memory", action="store_true", help="ajoute .claude/memory/ au .gitignore")
    ap.add_argument("--python", default="python" if os.name == "nt" else "python3",
                    help="interpréteur écrit dans les hooks (défaut : python sur Windows, python3 ailleurs)")
    a = ap.parse_args()

    project = Path(a.project).resolve()
    if not project.is_dir():
        sys.exit(f"Dossier introuvable : {project}")
    if a.file_map:
        src = json.loads(Path(a.file_map).read_text(encoding="utf-8")).get("source")
        if src and project.is_relative_to(Path(src).resolve()):
            sys.exit("Le projet est dans le dossier source de l'export, qui ne doit jamais être modifié.")
    stamp = time.strftime("%Y-%m-%d %H:%M")
    claude = project / ".claude"
    settings = read_settings(claude / "settings.json")  # valider avant toute écriture
    mem = claude / "memory"

    for fname, text in memory_files(a.name, stamp, changes_from_map(a.file_map, stamp)).items():
        write_new(mem / fname, text)
    (mem / "archives").mkdir(parents=True, exist_ok=True)
    write_new(mem / "archives" / ".gitkeep", "")

    for fname in ("PROTOCOLE.md", "GRAPHE.md"):
        text = (TPL / "memory" / fname).read_text(encoding="utf-8")
        write_new(mem / fname, text.replace("python3 .claude/hooks/", f"{a.python} .claude/hooks/"))

    hook_dst = claude / "hooks" / "graph_hook.py"
    if write_new(hook_dst, (TPL / "hooks" / "graph_hook.py").read_text(encoding="utf-8")):
        hook_dst.chmod(0o755)
    (claude / "graph").mkdir(parents=True, exist_ok=True)

    added_events = merge_settings(claude / "settings.json", settings, a.python)
    install_claude_md(project / "CLAUDE.md", a.name, a.python)
    ignored = merge_gitignore(project / ".gitignore", a.private_memory)

    py_exe = shutil.which(a.python) or sys.executable
    idx = run_hook(project, py_exe, ["index"])
    events = claude / "graph" / "events.jsonl"
    history = events.read_bytes() if events.exists() else None
    test = run_hook(project, py_exe, [], stdin=b'{"hook_event_name":"SessionStart","session_id":"scaffold"}')
    hook_ok = test.returncode == 0 and b"additionalContext" in test.stdout
    # l'événement de test ne fait pas partie de l'historique du projet
    if history is None:
        events.unlink(missing_ok=True)
    else:
        events.write_bytes(history)

    rel = lambda p: p.relative_to(project).as_posix()
    print(f"Préproduction Claude Code : {project}")
    print(f"  Créés ({len(created)}) : " + ", ".join(rel(p) for p in created))
    if skipped:
        print(f"  Déjà présents, non modifiés ({len(skipped)}) : " + ", ".join(rel(p) for p in skipped))
    print(f"  Hooks ajoutés à .claude/settings.json : {', '.join(added_events) or 'déjà présents'}")
    print(f"  .gitignore complété : {', '.join(ignored) or 'rien à ajouter'}")
    print(f"  Graphe : {idx.stdout.decode('utf-8', 'replace').strip() or idx.stderr.decode('utf-8', 'replace').strip()}")
    print(f"  Test du hook SessionStart : {'ok' if hook_ok else 'ÉCHEC — ' + test.stderr.decode('utf-8', 'replace')}")
    print(f"  Interpréteur des hooks : {a.python} (à ajuster si l'équipe mélange Windows et macOS/Linux)")
    print("À remplir à la main : etat.md (objectif, prochaine étape), decisions.md, problemes.md.")
    if not hook_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
