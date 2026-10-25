#!/usr/bin/env python3
"""design-to-dev : inventaire, vérification de plan, application et vérification.

Le dossier source n'est jamais modifié : `apply` copie vers une cible neuve.

  organize.py inventory <source> [--out inventory.json]
  organize.py plan-check <plan.json> [--inventory inventory.json]
  organize.py apply <plan.json> [--apply] [--force]
  organize.py verify <dossier>
"""
import argparse
import hashlib
import json
import os
import posixpath
import re
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

# --------------------------------------------------------------------------- classification

COLLAPSED_DIRS = {"node_modules", ".git", ".next", ".nuxt", ".turbo", ".cache", ".parcel-cache",
                  "__pycache__", ".venv", "venv", "coverage", ".svelte-kit", ".expo"}
BUILD_DIRS = {"dist", "build", "out"} | COLLAPSED_DIRS - {".git"}
TOOL_DIRS = {".bolt", ".lovable", ".vercel", ".netlify", ".replit", ".idea", ".figma"}
OS_JUNK = {".ds_store", "thumbs.db", "desktop.ini", "ehthumbs.db", "icon\r"}
TOOL_FILES = {".thumbnail", "thumbnail.html", "thumbnail.png", "_ds_manifest.json",
              "_adherence.oxlintrc.json", "replit.nix", ".replit"}

KINDS = {
    "code": {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte", ".py", ".go", ".rs",
             ".java", ".kt", ".swift", ".dart", ".php", ".rb", ".sh", ".ps1"},
    "style": {".css", ".scss", ".sass", ".less", ".styl"},
    "markup": {".html", ".htm"},
    "doc": {".md", ".mdx", ".txt", ".rst", ".pdf", ".docx"},
    "data": {".csv", ".tsv", ".xml"},
    "config": {".json", ".yaml", ".yml", ".toml", ".ini", ".env", ".lock", ".lockb", ".editorconfig"},
    "image": {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif", ".ico", ".bmp", ".tif", ".tiff", ".heic"},
    "font": {".woff", ".woff2", ".ttf", ".otf", ".eot"},
    "video": {".mp4", ".webm", ".mov", ".avi", ".mkv"},
    "audio": {".mp3", ".wav", ".ogg", ".m4a", ".flac"},
    "design-source": {".fig", ".sketch", ".psd", ".ai", ".xd", ".penpot", ".afdesign", ".blend"},
    "archive": {".zip", ".rar", ".7z", ".tar", ".gz"},
}
EXT_KIND = {e: k for k, exts in KINDS.items() for e in exts}

BACKUP_RE = re.compile(r"( copy\b|\(\d+\)|[-_ ](old|bak|backup)\b|\.bak$|\.orig$|final[-_ ]?final|~$)", re.I)
HASH_RE = re.compile(r"^[0-9a-f]{16,}$", re.I)
PASTED_RE = re.compile(r"^(pasted-|screenshot|screen shot|capture d.?[ée]cran|image ?\(\d+\)|img_\d+)", re.I)
PERSONAL_RE = re.compile(r"(^|[-_ ])(pp|profile|photo|selfie|portrait|passport|passeport|id[-_ ]?card|cni)([-_ .]|$)", re.I)
SECRET_NAME_RE = re.compile(r"^(\.env(\..+)?|.*\.pem|.*\.key|id_rsa.*|.*\.p12|credentials.*\.json)$", re.I)
GENERATED_MARK = re.compile(rb"(@ds-bundle|@generated|DO NOT EDIT|auto-?generated|webpackBootstrap)", re.I)

# --------------------------------------------------------------------------- références

TEXT_EXT = KINDS["code"] | KINDS["style"] | KINDS["markup"] | {".md", ".mdx", ".svg"}
JS_EXT = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte"}
MAX_SCAN = 4 * 1024 * 1024
ASSET_EXT = r"(?:png|jpe?g|gif|svg|webp|avif|ico|css|js|jsx|mjs|ts|tsx|json|woff2?|ttf|otf|eot|mp4|webm|mp3|wav|html?|pdf)"

PAT = {
    "attr": re.compile(r"""\b(?:src|href|data-src|poster)\s*=\s*["'](?P<p>[^"'#?{}<>]+)"""),
    "url": re.compile(r"""url\(\s*["']?(?P<p>[^"')?#{}]+)"""),
    "css-import": re.compile(r"""@import\s+["'](?P<p>[^"']+)["']"""),
    "js-from": re.compile(r"""\bfrom\s+["'](?P<p>[^"']+)["']"""),
    "js-import": re.compile(r"""\bimport\s*\(?\s*["'](?P<p>[^"']+)["']"""),
    "require": re.compile(r"""\brequire\(\s*["'](?P<p>[^"']+)["']"""),
    "md-link": re.compile(r"""\]\((?P<p>[^)\s#?]+)"""),
    "backtick": re.compile(r"""`(?P<p>[\w@./-]+\.[A-Za-z0-9]{1,6})`"""),
    "string": re.compile(r"""["'`](?P<p>(?:\.{1,2}/|/)?[\w@%.-]+(?:/[\w@%. -]+)*\.""" + ASSET_EXT + r""")["'`]"""),
}
# patterns « forts » : une référence non résolue est un vrai lien cassé
STRONG = {"attr", "url", "css-import", "js-from", "js-import", "require", "md-link"}
# patterns dont la cible n'est retenue que si elle existe
WEAK = {"backtick", "string"}
SKIP_PREFIX = ("http:", "https:", "//", "data:", "mailto:", "tel:", "javascript:", "#", "blob:", "about:")
IMPORT_EXTS = ("", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".css", ".json", "/index.js", "/index.jsx",
               "/index.ts", "/index.tsx", "/index.html")


def patterns_for(ext):
    if ext in (".html", ".htm", ".svg"):
        return ["css-import", "js-from", "js-import", "attr", "url"]
    if ext in KINDS["style"]:
        return ["css-import", "url"]
    if ext in JS_EXT:
        return ["js-from", "js-import", "require", "attr", "url", "string"]
    if ext in (".md", ".mdx"):
        return ["md-link", "attr", "backtick"]
    return []


def is_local(raw):
    r = raw.strip()
    if not r or r != raw or r.lower().startswith(SKIP_PREFIX):
        return False
    return not any(t in r for t in ("${", "{{", " + ", "…", "<", ">"))


def looks_like_path(raw):
    return "/" in raw or "." in raw


def is_module_spec(raw):
    """`react`, `@scope/pkg` : dépendance npm, pas un fichier."""
    return not raw.startswith((".", "/"))


def resolve(files, base_dir, raw, try_exts=False):
    raw = unquote(raw.strip())
    if raw.startswith("/"):
        cand = posixpath.normpath(raw.lstrip("/"))
    else:
        cand = posixpath.normpath(posixpath.join(base_dir, raw)) if base_dir else posixpath.normpath(raw)
    if cand.startswith("..") or cand == ".":
        return None, ""
    exts = IMPORT_EXTS if try_exts else ("", "/index.html")
    for e in exts:
        c = cand + e
        if c in files:
            return c, e
        low = files.get("__lower__", {}).get(c.lower())
        if low:
            return low, e
    return None, ""


def scan_refs(files, rel, data, loaders=()):
    """Retourne les références trouvées dans `data` (texte) du fichier `rel`."""
    ext = posixpath.splitext(rel)[1].lower()
    fdir = posixpath.dirname(rel)
    refs, taken = [], []
    for name in patterns_for(ext):
        for m in PAT[name].finditer(data):
            s, e = m.span("p")
            if any(a < e and s < b for a, b in taken):
                continue
            raw = m.group("p")
            if not is_local(raw):
                continue
            imp = name in ("js-from", "js-import", "require")
            if imp and is_module_spec(raw):
                continue
            if imp or ext in (".html", ".htm", ".svg") or ext in KINDS["style"]:
                bases = [("file", fdir)]
            elif ext in (".md", ".mdx"):
                bases = [("file", fdir), ("root", "")]
            else:  # chemin résolu à l'exécution par le document qui charge le script
                bases = [("doc:" + d, posixpath.dirname(d)) for d in loaders] + [("file", fdir), ("root", "")]
            target, base, suffix = None, None, ""
            for bname, bdir in bases:
                target, suffix = resolve(files, bdir, raw, try_exts=imp)
                if target:
                    base = bname
                    break
            if not target and (name in WEAK or not looks_like_path(raw)):
                continue
            taken.append((s, e))
            refs.append({"raw": raw, "kind": name, "span": [s, e], "resolved": target,
                         "base": base, "suffix": suffix})
    return refs


# --------------------------------------------------------------------------- inventaire

def walk(root):
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir
        keep = []
        for d in sorted(dirnames):
            if os.path.islink(os.path.join(dirpath, d)):
                # un lien peut pointer hors de la source : on ne le suit jamais
                print(f"  lien symbolique ignoré : {posixpath.join(rel_dir, d)}/", file=sys.stderr)
            elif d in COLLAPSED_DIRS:
                yield posixpath.join(rel_dir, d) + "/", True
            else:
                keep.append(d)
        dirnames[:] = keep
        for f in sorted(filenames):
            if os.path.islink(os.path.join(dirpath, f)):
                print(f"  lien symbolique ignoré : {posixpath.join(rel_dir, f)}", file=sys.stderr)
                continue
            yield posixpath.join(rel_dir, f), False


def dir_size(p):
    total = 0
    for dp, _, fs in os.walk(p):
        for f in fs:
            try:
                total += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return total


def signals_for(rel, size, head, is_dir):
    name = posixpath.basename(rel.rstrip("/"))
    low = name.lower()
    stem, ext = posixpath.splitext(low)
    parts = set(rel.lower().split("/"))
    sig = []
    if is_dir:
        sig.append("build-dir" if name in BUILD_DIRS else "vcs" if name == ".git" else "env-dir")
        return sig
    if low in OS_JUNK or low.startswith(("._", "~$")) or "__macosx" in parts or ext == ".tmp":
        sig.append("os-junk")
    if parts & BUILD_DIRS:
        sig.append("build-dir")
    if parts & TOOL_DIRS or low in TOOL_FILES or (rel.lower() == "skill.md"):
        sig.append("tool-artifact")
    if ext == ".log":
        sig.append("log")
    if (".min." in low or (name.startswith("_") and ext in (".js", ".json"))
            or (ext in (".js", ".css") and size > 500_000) or GENERATED_MARK.search(head or b"")):
        sig.append("generated")
    if BACKUP_RE.search(stem) or ext in (".bak", ".orig"):
        sig.append("backup-copy")
    if HASH_RE.match(stem.split("-")[0]):
        sig.append("hash-name")
    if PASTED_RE.match(stem):
        sig.append("pasted")
    if EXT_KIND.get(ext) == "image" and (PERSONAL_RE.search(stem) or
                                         ("uploads" in parts and not PASTED_RE.match(stem)
                                          and not HASH_RE.match(stem.split("-")[0]))):
        sig.append("personal-data?")
    if SECRET_NAME_RE.match(low) and low != ".env.example":
        sig.append("secret?")
    if size > 1_000_000:
        sig.append("large")
    return sig


def build_inventory(source):
    source = Path(source).resolve()
    if not source.is_dir():
        sys.exit(f"Dossier introuvable : {source}")
    entries, texts = {}, {}
    for rel, is_dir in walk(source):
        p = source / rel
        if is_dir:
            entries[rel] = {"path": rel, "kind": "dir-collapsed", "size": dir_size(p), "sha1": None,
                            "signals": signals_for(rel, 0, b"", True)}
            continue
        try:
            raw = p.read_bytes()
        except OSError as exc:
            print(f"  ! lecture impossible {rel}: {exc}", file=sys.stderr)
            continue
        ext = p.suffix.lower()
        kind = EXT_KIND.get(ext, "unknown" if ext else "unknown")
        entries[rel] = {"path": rel, "kind": kind, "size": len(raw), "sha1": hashlib.sha1(raw).hexdigest(),
                        "signals": signals_for(rel, len(raw), raw[:400], False)}
        if ext in TEXT_EXT and len(raw) <= MAX_SCAN:
            texts[rel] = raw.decode("utf-8", errors="surrogateescape")

    files = {k: True for k in entries if not k.endswith("/")}
    files["__lower__"] = {k.lower(): k for k in entries if not k.endswith("/")}

    # passe 1 : références, puis documents qui chargent chaque script ; passe 2 avec ces documents
    refs = {rel: scan_refs(files, rel, data) for rel, data in texts.items()}
    loaders = defaultdict(list)
    for rel, rs in refs.items():
        if rel.lower().endswith((".html", ".htm")):
            for r in rs:
                if r["resolved"]:
                    loaders[r["resolved"]].append(rel)
    for rel in texts:
        if loaders.get(rel) and posixpath.splitext(rel)[1].lower() in JS_EXT:
            refs[rel] = scan_refs(files, rel, texts[rel], loaders[rel])

    refs_in = defaultdict(set)
    for rel, rs in refs.items():
        for r in rs:
            if r["resolved"] and r["resolved"] != rel:
                refs_in[r["resolved"]].add(rel)

    by_hash = defaultdict(list)
    for e in entries.values():
        if e["sha1"] and e["size"] > 0:
            by_hash[e["sha1"]].append(e["path"])
    for paths in by_hash.values():
        if len(paths) > 1:
            for pth in paths:
                entries[pth]["signals"].append("duplicate")
                entries[pth]["duplicates"] = [x for x in paths if x != pth]

    for rel, e in entries.items():
        e["refs_out"] = refs.get(rel, [])
        e["refs_in"] = sorted(refs_in.get(rel, ()))
        e["loaded_by"] = loaders.get(rel, [])
        if not e["refs_in"] and not rel.endswith("/") and e["kind"] != "markup":
            if posixpath.basename(rel).lower() not in ("index.html", "readme.md", "license", "license.md"):
                e["signals"].append("orphan")
    return {"source": source.as_posix(), "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "files": entries}


def human(n):
    for unit in ("o", "Ko", "Mo", "Go"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "o" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} To"


def print_summary(inv):
    files = list(inv["files"].values())
    total = sum(f["size"] for f in files)
    print(f"Source : {inv['source']}\n{len(files)} entrées, {human(total)}\n")
    print("Par type :")
    kinds = defaultdict(lambda: [0, 0])
    for f in files:
        kinds[f["kind"]][0] += 1
        kinds[f["kind"]][1] += f["size"]
    for k, (c, s) in sorted(kinds.items(), key=lambda x: -x[1][1]):
        print(f"  {k:<15} {c:>5}  {human(s):>10}")
    print("\nPar dossier racine :")
    tops = defaultdict(lambda: [0, 0])
    for f in files:
        top = f["path"].split("/")[0] + ("/" if "/" in f["path"] else "")
        tops[top][0] += 1
        tops[top][1] += f["size"]
    for k, (c, s) in sorted(tops.items(), key=lambda x: -x[1][1]):
        pct = 100 * s / total if total else 0
        print(f"  {k:<32} {c:>5}  {human(s):>10}  {pct:4.0f} %")
    print("\nSignaux :")
    sigs = defaultdict(list)
    for f in files:
        for s in f["signals"]:
            sigs[s].append(f["path"])
    for s, paths in sorted(sigs.items(), key=lambda x: -len(x[1])):
        ex = ", ".join(paths[:4]) + (" …" if len(paths) > 4 else "")
        print(f"  {s:<16} {len(paths):>4}  {ex}")
    print("\nPlus gros fichiers :")
    for f in sorted(files, key=lambda x: -x["size"])[:8]:
        print(f"  {human(f['size']):>10}  {f['path']}")
    broken = [(f["path"], r["raw"]) for f in files for r in f["refs_out"]
              if not r["resolved"] and r["kind"] in STRONG]
    print(f"\nRéférences locales déjà cassées dans la source : {len(broken)}")
    for p, raw in broken[:10]:
        print(f"  {p} -> {raw}")


# --------------------------------------------------------------------------- plan

def glob_re(pattern):
    out, i = "", 0
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith("**", i):
            out += ".*"
            i += 2
            if i < len(pattern) and pattern[i] == "/":
                i += 1
            continue
        out += "[^/]*" if c == "*" else "[^/]" if c == "?" else re.escape(c)
        i += 1
    return re.compile("^" + out + "$")


def glob_prefix(pattern):
    head = re.split(r"[*?]", pattern, maxsplit=1)[0]
    return head[: head.rfind("/") + 1] if "/" in head else ""


def expand_plan(plan, paths):
    """Associe chaque chemin d'inventaire à une action. Explicite > glob le plus long."""
    explicit, globs = {}, []
    for a in plan.get("actions", []):
        src = a.get("src", "")
        (globs.append((len(src), glob_re(src), a)) if any(c in src for c in "*?") else explicit.__setitem__(src, a))
    globs.sort(key=lambda g: -g[0])
    resolved, used = {}, set()
    for p in paths:
        a = explicit.get(p) or explicit.get(p.rstrip("/"))
        if a is None:
            for _, rx, ga in globs:
                if rx.match(p) or rx.match(p.rstrip("/")):
                    a = dict(ga)
                    if a.get("action") == "move" and a.get("dst", "").endswith("/"):
                        a["dst"] = a["dst"] + p[len(glob_prefix(ga["src"])):]
                    break
        if a is not None:
            resolved[p] = a
            used.add(a.get("src"))
    unused = [a["src"] for a in plan.get("actions", []) if a.get("src") not in used]
    return resolved, unused


def target_of(path, a):
    act = a.get("action")
    if act == "delete":
        return None
    if act == "keep":
        return path
    dst = a.get("dst", "")
    if dst.endswith("/") and not path.endswith("/"):
        dst = dst + posixpath.basename(path)
    return dst


def check_plan(plan, inv):
    errors, warnings = [], []
    paths = list(inv["files"].keys())
    resolved, unused = expand_plan(plan, paths)
    for u in unused:
        warnings.append(f"entrée du plan sans fichier correspondant : {u}")
    mapping, dsts = {}, defaultdict(list)
    for p in paths:
        a = resolved.get(p)
        if a is None:
            errors.append(f"aucune action pour : {p}")
            continue
        act = a.get("action")
        if act not in ("keep", "move", "delete"):
            errors.append(f"action invalide '{act}' pour {p}")
            continue
        if act == "move" and not a.get("dst"):
            errors.append(f"move sans dst : {p}")
            continue
        if not a.get("reason"):
            warnings.append(f"pas de raison : {p}")
        t = target_of(p, a)
        if t is not None:
            t = posixpath.normpath(t.replace("\\", "/")) + ("/" if p.endswith("/") else "")
            if t.startswith(("..", "/")) or re.match(r"^[A-Za-z]:", t):
                errors.append(f"dst hors de la cible : {p} -> {t}")
                continue
            if t.lower().startswith("docs/cleanup/"):
                errors.append(f"docs/cleanup/ est réservé au rapport : {p} -> {t}")
                continue
            dsts[t.lower()].append(p)
        mapping[p] = t
    for t, srcs in dsts.items():
        if len(srcs) > 1:
            errors.append(f"collision vers {t} : {', '.join(srcs)}")
    file_dsts = {t for t in dsts if not t.endswith("/")}
    for t, srcs in dsts.items():
        parts = t.rstrip("/").split("/")
        clash = next(("/".join(parts[:i]) for i in range(1, len(parts)) if "/".join(parts[:i]) in file_dsts), None)
        if clash:
            errors.append(f"{clash} serait à la fois un fichier et un dossier (via {srcs[0]})")
    for p, t in mapping.items():
        if t is not None:
            continue
        a = resolved[p]
        rb = a.get("replaced_by")
        if rb and mapping.get(rb) is None:
            errors.append(f"{p} remplacé par {rb}, qui n'est pas conservé")
        live = [r for r in inv["files"][p]["refs_in"] if mapping.get(r) is not None]
        strong = [r for r in live if any(o["resolved"] == p and o["kind"] in STRONG
                                         for o in inv["files"][r]["refs_out"])]
        if strong and not rb:
            errors.append(f"suppression d'un fichier utilisé : {p} (référencé par {', '.join(strong[:3])})")
        elif live and not rb:
            warnings.append(f"{p} est seulement mentionné par {', '.join(live[:3])} : mettre ce texte à jour")
    reviews = [p for p, a in resolved.items() if a.get("review")]
    return errors, warnings, reviews, mapping, resolved


def print_tree(mapping, inv):
    tree = defaultdict(lambda: [0, 0])
    for p, t in mapping.items():
        if t is None:
            continue
        d = posixpath.dirname(t.rstrip("/")) or "."
        parts = d.split("/")
        for i in range(1, min(len(parts), 3) + 1):
            k = "/".join(parts[:i])
            tree[k][0] += 1
            tree[k][1] += inv["files"][p]["size"]
    print("Arborescence cible (3 niveaux) :")
    for k in sorted(tree):
        depth = 0 if k == "." else k.count("/") + 1
        name = "(racine)" if k == "." else posixpath.basename(k) + "/"
        print(f"  {'  ' * depth}{name:<34} {tree[k][0]:>4} fichiers  {human(tree[k][1]):>10}")


# --------------------------------------------------------------------------- application

def rel_from(base_dir, target):
    r = posixpath.relpath(target, base_dir or ".")
    return r


def rewrite(text, refs, old_path, new_path, mapping, resolved_actions):
    """Réécrit les chemins de `text` (contenu de old_path, copié en new_path)."""
    broken, changes = [], 0
    out = text
    for r in sorted(refs, key=lambda x: -x["span"][0]):
        tgt = r["resolved"]
        if not tgt:
            continue
        new_tgt = mapping.get(tgt)
        if new_tgt is None:
            rb = (resolved_actions.get(tgt) or {}).get("replaced_by")
            new_tgt = mapping.get(rb) if rb else None
        if new_tgt is None:
            broken.append((r["raw"], tgt))
            continue
        base = r["base"] or "file"
        if base == "file":
            old_base, new_base = posixpath.dirname(old_path), posixpath.dirname(new_path)
        elif base == "root":
            old_base = new_base = ""
        else:
            doc = base[4:]
            if mapping.get(doc) is None:
                continue
            old_base, new_base = posixpath.dirname(doc), posixpath.dirname(mapping[doc])
        if tgt == new_tgt and old_base == new_base:
            continue
        raw = r["raw"]
        if raw.startswith("/"):
            new_raw = "/" + new_tgt
        else:
            new_raw = rel_from(new_base, new_tgt)
            if raw.startswith("./") and not new_raw.startswith("."):
                new_raw = "./" + new_raw
        suffix = r.get("suffix") or ""
        if suffix and new_raw.endswith(suffix):  # import sans extension / dossier index
            new_raw = new_raw[: -len(suffix)] or "."
        if "%20" in raw:
            new_raw = new_raw.replace(" ", "%20")
        if new_raw != raw:
            s, e = r["span"]
            out = out[:s] + new_raw + out[e:]
            changes += 1
    return out, changes, broken


def apply_plan(plan_path, do_apply, force):
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    source, target = Path(plan["source"]), Path(plan["target"])
    src_r, tgt_r = source.resolve(), target.resolve()
    if src_r == tgt_r or tgt_r.is_relative_to(src_r) or src_r.is_relative_to(tgt_r):
        sys.exit("La cible et la source ne doivent pas être imbriquées l'une dans l'autre.")
    inv = build_inventory(source)
    errors, warnings, reviews, mapping, resolved = check_plan(plan, inv)
    for w in warnings[:30]:
        print("  avertissement :", w)
    if errors:
        print(f"\n{len(errors)} erreur(s) dans le plan :")
        for e in errors[:60]:
            print("  ✗", e)
        sys.exit(1)
    kept = {p: t for p, t in mapping.items() if t is not None}
    deleted = [p for p, t in mapping.items() if t is None]
    moved = [p for p, t in kept.items() if t != p]
    freed = sum(inv["files"][p]["size"] for p in deleted)
    print_tree(mapping, inv)
    print(f"\nGardés : {len(kept)} (dont déplacés : {len(moved)})  ·  supprimés : {len(deleted)}  ·  "
          f"gain : {human(freed)}  ·  à revoir : {len(reviews)}")
    if not do_apply:
        print("\nDry-run : rien n'a été écrit. Relancer avec --apply après validation de l'utilisateur.")
        return
    if reviews:
        print("\nÉléments encore marqués review (à trancher avec l'utilisateur) :")
        for p in reviews[:40]:
            print("  ?", p)
        sys.exit(1)
    if target.exists() and any(target.iterdir()) and not force:
        sys.exit(f"La cible n'est pas vide : {target} (utiliser --force seulement si l'utilisateur l'a demandé)")
    target.mkdir(parents=True, exist_ok=True)

    total_changes, all_broken = 0, []
    for old, new in kept.items():
        src_p, dst_p = source / old.rstrip("/"), target / new.rstrip("/")
        if not dst_p.resolve().is_relative_to(tgt_r) or dst_p.resolve().is_relative_to(src_r):
            sys.exit(f"Destination refusée (sort de la cible) : {new}")
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        if old.endswith("/"):
            shutil.copytree(src_p, dst_p, dirs_exist_ok=True, symlinks=True, ignore_dangling_symlinks=True)
            continue
        refs = inv["files"][old]["refs_out"]
        if refs:
            text = src_p.read_bytes().decode("utf-8", errors="surrogateescape")
            new_text, n, broken = rewrite(text, refs, old, new, mapping, resolved)
            dst_p.write_bytes(new_text.encode("utf-8", errors="surrogateescape"))
            shutil.copystat(src_p, dst_p)
            total_changes += n
            all_broken += [(new, raw, tgt) for raw, tgt in broken]
        else:
            shutil.copy2(src_p, dst_p)

    report_dir = target / "docs" / "cleanup"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d %H:%M")
    file_map = {"source": source.as_posix(), "target": target.as_posix(), "date": stamp,
                "files": [{"src": p, "dst": mapping[p], "action": resolved[p]["action"],
                           "reason": resolved[p].get("reason", ""), "replaced_by": resolved[p].get("replaced_by")}
                          for p in sorted(mapping)]}
    (report_dir / "file-map.json").write_text(json.dumps(file_map, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# Rapport de nettoyage — {stamp}", "",
             f"- Source (intacte) : `{source.as_posix()}`", f"- Cible : `{target.as_posix()}`",
             f"- Gardés : {len(kept)} (déplacés : {len(moved)}) · Supprimés : {len(deleted)} · Gain : {human(freed)}",
             f"- Chemins réécrits : {total_changes} · Références vers des fichiers supprimés : {len(all_broken)}", "",
             "## Supprimés", "", "| Fichier | Taille | Raison |", "|---|---|---|"]
    by_reason = defaultdict(list)
    for p in sorted(deleted):
        by_reason[resolved[p].get("reason", "")].append(p)
    for reason, ps in sorted(by_reason.items(), key=lambda x: -len(x[1])):
        size = human(sum(inv["files"][p]["size"] for p in ps))
        label = f"`{ps[0]}`" if len(ps) == 1 else f"`{ps[0]}` et {len(ps) - 1} autre(s)"
        lines.append(f"| {label} | {size} | {reason} |")
    lines += ["", "## Déplacés", "", "| Avant | Après |", "|---|---|"]
    lines += [f"| `{p}` | `{kept[p]}` |" for p in sorted(moved)]
    if all_broken:
        lines += ["", "## Références vers des fichiers supprimés (à corriger)", ""]
        lines += [f"- `{f}` → `{raw}` (était `{tgt}`)" for f, raw, tgt in all_broken]
    (report_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nCible écrite : {target}\nChemins réécrits : {total_changes}\n"
          f"Rapport : {report_dir / 'report.md'}\nFile map : {report_dir / 'file-map.json'}")
    if all_broken:
        print(f"{len(all_broken)} référence(s) vers des fichiers supprimés — voir le rapport.")


# --------------------------------------------------------------------------- vérification

def verify(folder):
    inv = build_inventory(folder)
    broken = [(f["path"], r["raw"], r["kind"]) for f in inv["files"].values() for r in f["refs_out"]
              if not r["resolved"] and r["kind"] in STRONG]
    junk = [f["path"] for f in inv["files"].values() if {"os-junk", "secret?"} & set(f["signals"])]
    names = [f["path"] for f in inv["files"].values()
             if re.search(r"[ À-ſ]", f["path"]) and not f["path"].startswith("docs/cleanup/")]
    print(f"{len(inv['files'])} fichiers vérifiés dans {inv['source']}")
    print(f"\nRéférences locales cassées : {len(broken)}")
    for p, raw, k in broken[:80]:
        print(f"  ✗ {p} -> {raw}  [{k}]")
    if junk:
        print(f"\nFichiers à risque encore présents ({len(junk)}) :")
        for p in junk[:20]:
            print("  !", p)
    if names:
        print(f"\nChemins avec espaces ou accents ({len(names)}) :")
        for p in names[:20]:
            print("  ~", p)
    if not broken and not junk:
        print("\nOK — aucune référence cassée.")
    return 1 if broken else 0


# --------------------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("inventory")
    a.add_argument("source")
    a.add_argument("--out")
    b = sub.add_parser("plan-check")
    b.add_argument("plan")
    b.add_argument("--inventory")
    c = sub.add_parser("apply")
    c.add_argument("plan")
    c.add_argument("--apply", action="store_true")
    c.add_argument("--force", action="store_true")
    d = sub.add_parser("verify")
    d.add_argument("folder")
    args = ap.parse_args()

    if args.cmd == "inventory":
        if args.out and Path(args.out).resolve().is_relative_to(Path(args.source).resolve()):
            sys.exit("--out doit être en dehors du dossier source (la source n'est jamais modifiée).")
        inv = build_inventory(args.source)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(inv, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"Inventaire écrit : {args.out}\n")
        print_summary(inv)
    elif args.cmd == "plan-check":
        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        inv = (json.loads(Path(args.inventory).read_text(encoding="utf-8")) if args.inventory
               else build_inventory(plan["source"]))
        errors, warnings, reviews, mapping, _ = check_plan(plan, inv)
        for w in warnings[:40]:
            print("  avertissement :", w)
        for e in errors[:80]:
            print("  ✗", e)
        print(f"\n{len(errors)} erreur(s), {len(warnings)} avertissement(s), {len(reviews)} à revoir")
        for p in reviews[:40]:
            print("  ?", p)
        if not errors:
            print_tree(mapping, inv)
        sys.exit(1 if errors else 0)
    elif args.cmd == "apply":
        apply_plan(args.plan, args.apply, args.force)
    elif args.cmd == "verify":
        sys.exit(verify(args.folder))


if __name__ == "__main__":
    main()
