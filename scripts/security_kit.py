#!/usr/bin/env python3
"""design-to-dev : kit de skills de sécurité du projet (copie épinglée dans .claude/skills).

Les skills tierces retenues (Trail of Bits, UnitOne, Cloudflare) sont décrites dans
references/security-kit.json : dépôt, commit épinglé, licence et empreinte SHA-256 de chaque fichier.
L'installation télécharge l'archive de ce commit, vérifie chaque empreinte, scanne le contenu
(consignes cachées, Trojan Source, commandes exécutées au chargement, contournement des permissions,
binaires) et refuse une skill au moindre ❌. Rien de ce qui est téléchargé n'est exécuté.

  security_kit.py list [<projet>] [--json]
  security_kit.py install <projet> [--only a,b] [--optional] [--dry-run] [--yes] [--json]
  security_kit.py verify <projet> [--out docs/security/kit-securite.md] [--strict] [--json]
"""
import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

SKILL = Path(__file__).resolve().parent.parent
CATALOG_FILE = SKILL / "references" / "security-kit.json"
CATALOG_ENV = "DESIGN_TO_DEV_KIT_CATALOG"  # tests : catalogue de substitution
BASE_ENV = "DESIGN_TO_DEV_KIT_BASE"        # tests : remplace codeload.github.com par un serveur local
CODELOAD = "https://codeload.github.com"
LOCAL = {"127.0.0.1", "localhost", "::1"}
USER_AGENT = "design-to-dev (+https://github.com/duckysface/design-to-dev)"
TIMEOUT, MAX_ARCHIVE, MAX_FILE = 60, 200 * 1024 * 1024, 4 * 1024 * 1024
LOCK_REL = ".claude/security-kit.lock.json"
NOTICE_REL = ".claude/skills/THIRD_PARTY_NOTICES.md"
REPORT_REL = "docs/security/kit-securite.md"
START, END = "<!-- design-to-dev:securite:start -->", "<!-- design-to-dev:securite:end -->"
OK, WARN, BLOCK = "✅", "⚠️", "❌"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
MOMENTS = {
    "fondations": "Au départ du projet (fondations) et à chaque nouvelle brique (auth, API, paiement, IA…)",
    "code": "À chaque modification de code, avant de la déclarer terminée",
    "commit": "Avant chaque commit ou pull request",
}

# contrôles propres aux skills, en plus de ceux des fondations (Unicode, consignes cachées, code caché)
DYNAMIC_SHELL_RE = re.compile(r"!`[^`\n]+`")  # Claude Code exécute `!`cmd`` au chargement de la skill
PERMISSION_RE = re.compile(r"(?i)bypassPermissions|dangerously-skip-permissions|--dangerously-bypass|"
                           r"skipDangerousModePermissionPrompt|\"defaultMode\"\s*:\s*\"(?:bypassPermissions|acceptEdits)\"")
NETWORK_RE = re.compile(r"\b(?:urllib\.request|urlopen|requests\.(?:get|post)|http\.client|fetch\s*\(|"
                        r"https?\.request\s*\(|XMLHttpRequest|subprocess|child_process|os\.system)\b")
TOOLS_RE = re.compile(r"(?im)^allowed-tools:\s*(.+)$")
SCRIPT_EXT = {".py", ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd", ".js", ".cjs", ".mjs", ".ts", ".rb", ".pl"}
TEXT_EXT = {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".svg", ".lock", ".cfg", ".ini", ".xml", ".csv", ""}
TEXT_EXT |= SCRIPT_EXT


def load_foundations():
    spec = importlib.util.spec_from_file_location("d2d_foundations", Path(__file__).with_name("foundations.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_catalog():
    path = Path(os.environ.get(CATALOG_ENV) or CATALOG_FILE)
    data = json.loads(path.read_text(encoding="utf-8"))
    for s in data["skills"]:
        if not NAME_RE.match(s["name"]) or s["source"] not in data["sources"]:
            raise SystemExit(f"Catalogue invalide : {s.get('name')}")
    return data


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def safe_rel(rel):
    p = Path(rel)
    return not p.is_absolute() and ".." not in p.parts and rel == p.as_posix() and not rel.startswith("/")


# ---------------------------------------------------------------- sélection

def project_signals(root):
    """Ce que le projet utilise, pour proposer les skills conditionnelles (lecture seule, rien n'est exécuté)."""
    sig = {"github-actions": (root / ".github" / "workflows").is_dir(), "llm": False}
    llm = re.compile(r"(?i)[\"'\s/](openai|@anthropic-ai/[\w-]+|anthropic|langchain[\w-]*|@langchain/[\w-]+|"
                     r"@ai-sdk/[\w-]+|llamaindex|llama-index|ollama|@google/generative-ai|google-genai|"
                     r"mistralai|cohere|transformers|litellm)[\"'\s=<>~^@\n]")
    vercel_ai = re.compile(r"[\"']ai[\"']\s*:")  # SDK Vercel « ai » dans package.json
    for name in ("package.json", "requirements.txt", "pyproject.toml", "Cargo.toml", "composer.json", "go.mod"):
        for p in [root / name, *root.glob(f"*/{name}")]:
            try:
                if p.is_file() and p.stat().st_size < 2 * 1024 * 1024 and (llm.search(" " + p.read_text("utf-8", "replace"))
                                                                    or vercel_ai.search(p.read_text("utf-8", "replace"))):
                    sig["llm"] = True
            except OSError:
                pass
    return sig


def select(catalog, root, only=None, optional=False):
    """Skills proposées pour ce projet : défaut + conditionnelles détectées (+ optionnelles sur demande)."""
    by_name = {s["name"]: s for s in catalog["skills"]}
    if only:
        unknown = [n for n in only if n not in by_name]
        if unknown:
            raise SystemExit(f"Skill(s) hors catalogue : {', '.join(unknown)} — voir `security_kit.py list`")
        return [by_name[n] for n in only]
    sig = project_signals(root) if root else {}
    chosen = []
    for s in catalog["skills"]:
        when = s["when"]
        if when == "default" or (when == "opt-in" and optional) or sig.get(when):
            chosen.append(s)
    return chosen


# ---------------------------------------------------------------- téléchargement

def base_url():
    base = os.environ.get(BASE_ENV)
    if not base:
        return CODELOAD
    u = urllib.parse.urlparse(base)
    if u.scheme == "https" or (u.scheme == "http" and u.hostname in LOCAL):
        return base.rstrip("/")
    raise SystemExit(f"{BASE_ENV} doit être en https (ou http sur localhost)")


class Limited(io.RawIOBase):
    def __init__(self, raw, limit):
        self.raw, self.left = raw, limit

    def readable(self):
        return True

    def readinto(self, b):
        if self.left <= 0:
            raise ValueError(f"archive trop grosse (> {MAX_ARCHIVE // (1024 * 1024)} Mo)")
        n = self.raw.readinto(memoryview(b)[: min(len(b), self.left)])
        self.left -= n or 0
        return n


def fetch(source, wanted):
    """Télécharge l'archive du commit épinglé ; ne garde que les fichiers demandés (fichiers ordinaires seulement)."""
    url = f"{base_url()}/{source['repo']}/tar.gz/{source['sha']}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    got, refused = {}, []
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        with tarfile.open(fileobj=io.BufferedReader(Limited(resp, MAX_ARCHIVE)), mode="r|gz") as tar:
            for m in tar:
                parts = m.name.split("/", 1)
                if len(parts) < 2 or parts[1] not in wanted:
                    continue
                rel = parts[1]
                if not m.isfile():
                    refused.append(f"`{rel}` : lien ou fichier spécial dans l'archive")
                elif m.size > MAX_FILE:
                    refused.append(f"`{rel}` : fichier trop gros ({m.size} octets)")
                else:
                    got[rel] = tar.extractfile(m).read()
    return got, refused


# ---------------------------------------------------------------- scan

def scan_files(files, reviewed=()):
    """files : {chemin relatif: octets}. Renvoie [(niveau, contrôle, texte)]. `reviewed` déclasse un ❌ revu à la main."""
    f = load_foundations()
    rep = f.Report()
    texts = []
    for rel, data in sorted(files.items()):
        ext = Path(rel).suffix.lower()
        if ext in f.FOREIGN_BLOCK:
            rep.add(BLOCK, "binary", f"`{rel}` : exécutable ou binaire dans une skill")
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            rep.add(BLOCK, "binary", f"`{rel}` : fichier non textuel dans une skill")
            continue
        if ext not in TEXT_EXT:
            rep.add(WARN, "type", f"`{rel}` : type de fichier inattendu ({ext}) — le lire")
        texts.append((rel, text))
        for n, line in enumerate(text.splitlines(), 1):
            if DYNAMIC_SHELL_RE.search(line) and ext == ".md":
                rep.add(BLOCK, "load-exec", f"`{rel}:{n}` : commande shell exécutée au chargement de la skill "
                                            f"« {f.short(DYNAMIC_SHELL_RE.search(line).group(0))} »")
            if PERMISSION_RE.search(line):
                rep.add(BLOCK, "permissions", f"`{rel}:{n}` : contournement des permissions "
                                              f"« {f.short(PERMISSION_RE.search(line).group(0))} »")
        if Path(rel).name == "hooks.json" or re.search(r"(?m)^hooks:\s*$", text[:3000]):
            rep.add(BLOCK, "hooks", f"`{rel}` : la skill déclare des hooks (exécutés sans demander)")
        if ext in SCRIPT_EXT:
            net = " ; accès réseau ou processus" if NETWORK_RE.search(text) else ""
            rep.add(WARN, "script", f"`{rel}` : script{net} — ne jamais le lancer sans l'accord de l'utilisateur")
        if Path(rel).name == "SKILL.md":
            tools = TOOLS_RE.search(text[:3000])
            if tools and re.search(r"\b(Bash|Write|Edit|WebFetch|WebSearch|NotebookEdit)\b", tools.group(1)):
                rep.add(WARN, "tools", f"`{rel}` : outils autorisés « {f.short(tools.group(1), 80)} »")

    class P:  # chemin factice : les contrôles des fondations n'utilisent que relative_to().as_posix() et suffix
        def __init__(self, rel):
            self.rel, self.suffix = rel, Path(rel).suffix

        def relative_to(self, _):
            return Path(self.rel)

    pseudo = [(P(rel), text) for rel, text in texts]
    f.check_unicode(rep, pseudo, None)
    f.check_injection(rep, pseudo, None)
    f.check_hidden(rep, pseudo, None)
    out = []
    for level in (BLOCK, WARN):
        for check, text in rep.items[level]:
            why = next((r["why"] for r in reviewed if level == BLOCK and r["check"] == check
                        and text.startswith(f"`{r['file']}`")), None)
            out.append((WARN, check, f"{text} — revu : {why}") if why else (level, check, text))
    return out


# ---------------------------------------------------------------- installation

def license_rel(source):
    return source.get("license_file", "LICENSE")


def wanted_paths(skill, source):
    """{chemin dans l'archive: chemin dans la skill installée}"""
    paths = {f"{skill['path']}/{rel}": rel for rel in skill["files"] if rel != "LICENSE"}
    if "LICENSE" in skill["files"]:
        paths[license_rel(source)] = "LICENSE"
    return paths


def read_lock(root):
    p = root / LOCK_REL
    if not p.is_file():
        return {"skills": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data.get("skills"), dict) else {"skills": {}}
    except (OSError, ValueError):
        return {"skills": {}}


def local_state(root, name, entry):
    """'absente' | 'intacte' | 'modifiée' | 'étrangère' (dossier présent mais pas installé par le kit)."""
    d = root / ".claude" / "skills" / name
    if not d.exists():
        return "absente"
    if not entry:
        return "étrangère"
    for rel, h in entry["files"].items():
        p = d / rel
        if not p.is_file() or sha256(p.read_bytes()) != h:
            return "modifiée"
    return "intacte"


def write_skill(root, name, files):
    dest = root / ".claude" / "skills" / name
    tmp = dest.with_name(f".{name}.tmp-{os.getpid()}")
    if tmp.exists():
        shutil.rmtree(tmp)
    for rel, data in files.items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    if dest.exists():
        old = dest.with_name(f".{name}.old-{os.getpid()}")
        dest.rename(old)
        tmp.rename(dest)
        shutil.rmtree(old)
    else:
        tmp.rename(dest)


def notices(catalog, lock):
    lines = ["# Skills tierces — licences et attribution", "",
             "Copiées sans modification par `design-to-dev security-kit` depuis un commit épinglé ; chaque fichier est "
             f"vérifié par son empreinte SHA-256 (`{LOCK_REL}`). Les fichiers non copiés sont listés comme exclus.", ""]
    for name, e in sorted(lock["skills"].items()):
        src = catalog["sources"].get(e["source"], {})
        lines += [f"## {name}", f"- Auteur : {src.get('author', '?')}",
                  f"- Source : https://github.com/{e['repo']}/tree/{e['sha']}/{e['path']}",
                  f"- Licence : {e['license']} ({src.get('license_url', '')}) — texte complet dans `{name}/LICENSE`",
                  "- Modifications : aucune" + (f" ; fichiers exclus : {', '.join(e['excluded'])}" if e.get("excluded") else ""),
                  ""]
    return "\n".join(lines)


def install(root, catalog, chosen, dry_run=False):
    lock = read_lock(root)
    results = []
    by_source = {}
    for s in chosen:
        by_source.setdefault(s["source"], []).append(s)
    for src_key, skills in by_source.items():
        source = catalog["sources"][src_key]
        todo = []
        for s in skills:
            state = local_state(root, s["name"], lock["skills"].get(s["name"]))
            entry = lock["skills"].get(s["name"])
            if state == "étrangère":
                results.append({"name": s["name"], "status": "ignorée", "why": "un dossier du même nom existe déjà "
                                "(skill du projet, pas installée par le kit) — conservé"})
            elif state == "modifiée":
                results.append({"name": s["name"], "status": "ignorée", "why": "modifiée localement depuis "
                                "l'installation — conservée (supprimer le dossier pour réinstaller)"})
            elif state == "intacte" and entry["sha"] == source["sha"] and entry["files"] == s["files"]:
                results.append({"name": s["name"], "status": "à jour", "why": source["sha"][:12]})
            else:
                todo.append(s)
        if not todo:
            continue
        if dry_run:
            results += [{"name": s["name"], "status": "à installer", "why": f"{source['repo']}@{source['sha'][:12]}"}
                        for s in todo]
            continue
        wanted = {}
        for s in todo:
            wanted.update(wanted_paths(s, source))
        try:
            got, refused = fetch(source, set(wanted))
        except (urllib.error.URLError, OSError, ValueError, tarfile.TarError) as e:
            results += [{"name": s["name"], "status": "échec", "why": f"téléchargement impossible : {e}"} for s in todo]
            continue
        for s in todo:
            mapping = wanted_paths(s, source)
            files, problems = {}, [r for r in refused if any(r.startswith(f"`{k}`") for k in mapping)]
            for arc, rel in mapping.items():
                data = got.get(arc)
                if data is None:
                    problems.append(f"`{rel}` : absent de l'archive")
                elif sha256(data) != s["files"][rel]:
                    problems.append(f"`{rel}` : empreinte différente du catalogue (contenu modifié)")
                else:
                    files[rel] = data
            findings = scan_files(files, s.get("reviewed", [])) if not problems else []
            blocks = problems + [t for lv, _, t in findings if lv == BLOCK]
            if blocks:
                results.append({"name": s["name"], "status": "refusée", "why": blocks[0], "blocks": blocks,
                                "findings": [list(x) for x in findings]})
                continue
            write_skill(root, s["name"], files)
            lock["skills"][s["name"]] = {"source": src_key, "repo": source["repo"], "sha": source["sha"],
                                         "license": source["license"], "path": s["path"], "moments": s["moments"],
                                         "excluded": s.get("excluded", []), "files": s["files"],
                                         "installed": time.strftime("%Y-%m-%d")}
            results.append({"name": s["name"], "status": "installée", "why": f"{source['repo']}@{source['sha'][:12]}",
                             "findings": [list(x) for x in findings]})
    if not dry_run and any(r["status"] == "installée" for r in results):
        lock["catalog"] = catalog.get("checked")
        (root / ".claude").mkdir(parents=True, exist_ok=True)
        (root / LOCK_REL).write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
                                     newline="\n")
        (root / NOTICE_REL).write_text(notices(catalog, lock) + "\n", encoding="utf-8", newline="\n")
    return lock, results


# ---------------------------------------------------------------- mémoire

def rules_block(catalog, lock):
    by = {m: [] for m in MOMENTS}
    for name, e in sorted(lock["skills"].items()):
        use = next((s.get("use", "") for s in catalog["skills"] if s["name"] == name), "")
        for m in e.get("moments", []):
            if m in by:
                by[m].append(f"`{name}`" + (f" ({use})" if use and m == e["moments"][0] else ""))
    lines = ["## Kit de sécurité (OBLIGATOIRE, tous agents)", "",
             f"Skills de sécurité installées dans `.claude/skills/` (versions épinglées, `{LOCK_REL}`). "
             "Claude Code les charge seul ; les autres agents lisent `.claude/skills/<nom>/SKILL.md`.", ""]
    for m, label in MOMENTS.items():
        if by[m]:
            lines.append(f"- **{label}** : {', '.join(by[m])}.")
    lines += [
        "- Toujours aussi : `npx design-to-dev foundations .` après un ajout de dépendance ou de fichier tiers, et "
        "`npx design-to-dev security-kit verify .` avant un commit (empreintes des skills + scan de `.claude/`).",
        "- Un résultat de ces skills est un candidat à vérifier : le confirmer dans le code, puis le noter dans "
        "`.agents/memory/problemes.md` (faille) ou `decisions.md` (choix de correction).",
        "- Ne jamais lancer un script fourni par ces skills (ni une commande réseau) sans l'accord de l'utilisateur.",
        "- Ne jamais modifier les fichiers de ces skills : `security-kit verify` les compare à leurs empreintes.",
    ]
    return "\n".join(lines)


def upsert(path, body):
    block = f"{START}\n{body.strip()}\n{END}"
    text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if START in text and END in text and text.index(START) < text.index(END):
        new = text[: text.index(START)] + block + text[text.index(END) + len(END):]
    elif START in text or END in text:
        return False
    else:
        new = (text.rstrip() + "\n\n" if text.strip() else "") + block + "\n"
    if new != text:
        path.write_text(new, encoding="utf-8", newline="\n")
        return True
    return False


def update_memory(root, catalog, lock, installed):
    touched = []
    if lock["skills"] and upsert(root / "AGENTS.md", rules_block(catalog, lock)):
        touched.append("AGENTS.md")
    dec = root / ".agents" / "memory" / "decisions.md"
    if installed and dec.is_file():
        srcs = sorted({f"{e['repo']}@{e['sha'][:12]} ({e['license']})" for n, e in lock["skills"].items() if n in installed})
        entry = (f"\n## Kit de sécurité du projet ({time.strftime('%Y-%m-%d')})\n"
                 f"- Décision : skills de sécurité copiées dans `.claude/skills/` : {', '.join(sorted(installed))}.\n"
                 f"- Raison : vérifier les fondations puis chaque modification de code (règles dans AGENTS.md, "
                 f"section « Kit de sécurité »).\n- Sources épinglées : {', '.join(srcs)}.\n"
                 "- Alternatives écartées : skills de tests offensifs actifs, dépôts sans licence ou qui déclarent "
                 "des hooks ou des commandes exécutées au chargement.\n"
                 "- Validée par : l'utilisateur (accord avant installation).\n")
        dec.write_text(dec.read_text(encoding="utf-8").rstrip() + "\n" + entry, encoding="utf-8", newline="\n")
        touched.append(".agents/memory/decisions.md")
    return touched


# ---------------------------------------------------------------- vérification

def verify(root, catalog):
    """Empreintes des skills du kit + scan de tout `.claude/` et des fichiers d'instructions du projet."""
    items = []
    lock = read_lock(root)
    cat = {s["name"]: s for s in catalog["skills"]}
    trusted = set()
    for name, e in sorted(lock["skills"].items()):
        state = local_state(root, name, e)
        if state == "intacte":
            items.append((OK, "kit", f"`{name}` : intacte ({e['repo']}@{e['sha'][:12]})"))
            trusted |= {f".claude/skills/{name}/{rel}" for rel in e["files"]}
            if name in cat and cat[name]["files"] != e["files"]:
                items.append((WARN, "kit", f"`{name}` : une version plus récente est cataloguée — `security-kit install`"))
        elif state == "absente":
            items.append((WARN, "kit", f"`{name}` : supprimée du projet mais encore dans `{LOCK_REL}`"))
        else:
            items.append((BLOCK, "kit", f"`{name}` : fichiers modifiés depuis l'installation — comparer avec "
                                        f"https://github.com/{e['repo']}/tree/{e['sha']}/{e['path']}"))
    files = {}
    for base in (root / ".claude", root / ".agents" / "skills", root / ".codex"):
        if base.is_dir():
            for p in base.rglob("*"):
                rel = p.relative_to(root).as_posix()
                if p.is_file() and rel not in trusted and rel not in (LOCK_REL, NOTICE_REL) \
                        and "__pycache__" not in p.parts and p.stat().st_size <= MAX_FILE:
                    files[rel] = p.read_bytes()
    for name in ("CLAUDE.md", "AGENTS.md", "GEMINI.md", ".mcp.json"):
        if (root / name).is_file():
            files[name] = (root / name).read_bytes()
    for level, check, text in scan_files(files):
        if check in ("script", "tools", "type") and (text.startswith("`.claude/hooks/") or
                                                     text.startswith("`.agents/hooks/")):
            continue
        items.append((level, check, text))
    items += settings_checks(root)
    return lock, items, trusted


def settings_checks(root):
    """Hooks et permissions déclarés dans les réglages du projet : ce qui s'exécute sans demander."""
    out = []
    for rel in (".claude/settings.json", ".claude/settings.local.json", ".codex/hooks.json"):
        p = root / rel
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8-sig"))
        except ValueError:
            out.append((WARN, "settings", f"`{rel}` : JSON illisible"))
            continue
        perms = data.get("permissions", {}) if isinstance(data, dict) else {}
        if isinstance(perms, dict):
            for rule in perms.get("allow", []) or []:
                if isinstance(rule, str) and re.fullmatch(r"Bash(\(\*?\))?|Bash\(\s*\*\s*\)|\*", rule.strip()):
                    out.append((BLOCK, "settings", f"`{rel}` : permission « {rule} » — toute commande sans demander"))
            if perms.get("defaultMode") == "bypassPermissions":
                out.append((BLOCK, "settings", f"`{rel}` : defaultMode bypassPermissions"))
        hooks = data.get("hooks", {}) if isinstance(data, dict) else {}
        for event, entries in (hooks.items() if isinstance(hooks, dict) else []):
            for entry in entries if isinstance(entries, list) else []:
                for h in (entry.get("hooks", []) if isinstance(entry, dict) else []):
                    cmd = h.get("command", "") if isinstance(h, dict) else ""
                    if not cmd:
                        continue
                    level = WARN if re.search(r"(?i)\b(curl|wget|iwr|irm|invoke-webrequest|nc|ncat)\b|\|\s*(ba)?sh\b|"
                                              r"base64\s+-d", cmd) else OK
                    if level == OK and "memory_hook.py" not in cmd:
                        level = WARN
                    out.append((level, "hooks", f"`{rel}` : hook {event} « {cmd[:90]} »"
                                + ("" if level == OK else " — vérifier ce qu'il lance")))
    return out


def render_verify(lock, items, date):
    n = {lv: sum(1 for x in items if x[0] == lv) for lv in (OK, WARN, BLOCK)}
    lines = [f"# Kit de sécurité et configuration des agents — {date}", "",
             f"{n[OK]} ✅ · {n[WARN]} ⚠️ · {n[BLOCK]} ❌ — skills du kit : {len(lock['skills'])}", "",
             "Contrôles : empreintes des skills du kit, consignes cachées et caractères invisibles dans `.claude/`, "
             "`.agents/skills/`, `.codex/` et les fichiers d'instructions, commandes exécutées au chargement d'une "
             "skill, hooks et permissions des réglages.", "",
             "| | Contrôle | Détail |", "|---|---|---|"]
    order = {BLOCK: 0, WARN: 1, OK: 2}
    for level, check, text in sorted(items, key=lambda x: order[x[0]]):
        lines.append(f"| {level} | {check} | {text.replace('|', '¦')} |")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- CLI

def confirm(chosen, catalog, assume_yes):
    if assume_yes:
        return True
    need = "Accord requis : relancer avec --yes après l'accord de l'utilisateur."
    if not sys.stdin.isatty():
        print(need, file=sys.stderr)
        return False
    print("Skills à copier dans .claude/skills/ :")
    for s in chosen:
        src = catalog["sources"][s["source"]]
        print(f"  {s['name']:28} {src['repo']}@{src['sha'][:12]} ({src['license']})")
    try:
        answer = input("Installer ? [o/N] : ")
    except EOFError:  # NUL passe pour un terminal sous Windows
        print("\n" + need, file=sys.stderr)
        return False
    return answer.strip().lower() in ("o", "oui", "y", "yes")


def cmd_list(args, catalog):
    root = Path(args.project).resolve() if args.project else None
    lock = read_lock(root) if root else {"skills": {}}
    chosen = {s["name"] for s in select(catalog, root, optional=False)} if root else set()
    rows = []
    for s in catalog["skills"]:
        src = catalog["sources"][s["source"]]
        rows.append({"name": s["name"], "source": src["repo"], "sha": src["sha"], "license": src["license"],
                     "when": s["when"], "moments": s["moments"], "use": s.get("use", ""),
                     "proposed": s["name"] in chosen,
                     "state": local_state(root, s["name"], lock["skills"].get(s["name"])) if root else None})
    if args.json:
        print(json.dumps({"skills": rows, "plugins": catalog.get("plugins", [])}, ensure_ascii=False, indent=2))
        return 0
    for r in rows:
        flag = "→" if r["proposed"] else " "
        state = f" [{r['state']}]" if r["state"] else ""
        print(f"{flag} {r['name']:28} {r['when']:15} {r['source']} ({r['license']}){state}")
    for p in catalog.get("plugins", []):
        print(f"  plugin {p['name']} : {p['install']} — {p['why']}")
    return 0


def cmd_install(args, catalog):
    root = Path(args.project).resolve()
    if not root.is_dir():
        raise SystemExit(f"Dossier introuvable : {root}")
    only = [x.strip() for x in args.only.split(",") if x.strip()] if args.only else None
    chosen = select(catalog, root, only, args.optional)
    if not args.dry_run and not confirm(chosen, catalog, args.yes):
        return 2
    lock, results = install(root, catalog, chosen, args.dry_run)
    installed = [r["name"] for r in results if r["status"] == "installée"]
    touched = [] if args.dry_run else update_memory(root, catalog, lock, installed)
    if args.json:
        print(json.dumps({"results": results, "memory": touched, "lock": LOCK_REL}, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"{r['status']:12} {r['name']:28} {r['why']}")
            shown = [t for lv, _, t in r.get("findings", []) if lv != OK and "— revu :" not in t]
            for t in shown[:6]:
                print(f"             {WARN} {t}")
        if touched:
            print(f"Mémoire mise à jour : {', '.join(touched)}")
        if not args.dry_run and installed:
            print(f"Licences : {NOTICE_REL} — empreintes : {LOCK_REL}")
    return 1 if any(r["status"] in ("refusée", "échec") for r in results) else 0


def cmd_verify(args, catalog):
    root = Path(args.project).resolve()
    if not root.is_dir():
        raise SystemExit(f"Dossier introuvable : {root}")
    lock, items, _ = verify(root, catalog)
    out = Path(args.out) if args.out else root / REPORT_REL
    out = out if out.is_absolute() else Path.cwd() / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_verify(lock, items, time.strftime("%Y-%m-%d")), encoding="utf-8", newline="\n")
    n_block = sum(1 for x in items if x[0] == BLOCK)
    if args.json:
        print(json.dumps({"out": str(out), "skills": sorted(lock["skills"]), "block": n_block,
                          "items": [{"level": a, "check": b, "text": c} for a, b, c in items]},
                         ensure_ascii=False, indent=2))
    else:
        for level, _, text in items:
            if level != OK:
                print(f"  {level} {text}")
        print(f"{len(lock['skills'])} skill(s) du kit, {n_block} ❌ → {out}")
    return 1 if args.strict and n_block else 0


def trusted_files(root):
    """Fichiers des skills du kit intacts (empreintes du verrou = catalogue) : les fondations ne les rescannent pas,
    leurs exemples d'attaque cités ont été revus à l'épinglage."""
    try:
        catalog = {s["name"]: s for s in load_catalog()["skills"]}
    except (OSError, ValueError, KeyError, SystemExit):
        return set()
    out = set()
    for name, e in read_lock(root)["skills"].items():
        if name in catalog and catalog[name]["files"] == e["files"] and local_state(root, name, e) == "intacte":
            out |= {f".claude/skills/{name}/{rel}" for rel in e["files"]}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Kit de skills de sécurité du projet (.claude/skills, versions épinglées)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    li = sub.add_parser("list", help="catalogue et skills proposées pour le projet")
    li.add_argument("project", nargs="?")
    li.add_argument("--json", action="store_true")
    ins = sub.add_parser("install", help="copie les skills choisies dans <projet>/.claude/skills (avec accord)")
    ins.add_argument("project")
    ins.add_argument("--only", help="liste de skills (sinon : défaut + conditionnelles détectées)")
    ins.add_argument("--optional", action="store_true", help="ajoute les skills optionnelles (réseau, outils externes)")
    ins.add_argument("--dry-run", action="store_true", help="affiche ce qui serait installé, sans télécharger")
    ins.add_argument("-y", "--yes", action="store_true", help="accord déjà donné par l'utilisateur")
    ins.add_argument("--json", action="store_true")
    ve = sub.add_parser("verify", help="empreintes du kit + scan de .claude/ → docs/security/kit-securite.md")
    ve.add_argument("project")
    ve.add_argument("--out")
    ve.add_argument("--strict", action="store_true", help="code 1 s'il reste un ❌")
    ve.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    catalog = load_catalog()
    return {"list": cmd_list, "install": cmd_install, "verify": cmd_verify}[args.cmd](args, catalog)


if __name__ == "__main__":
    sys.exit(main())
