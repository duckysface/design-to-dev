#!/usr/bin/env python3
"""design-to-dev : intention du projet, écrans/démos déjà faits, besoins backend, skills compagnes.

Lecture seule : aucun fichier du dossier analysé n'est exécuté ni modifié.

  detect_project.py scan <dossier> [--out design-inventory.json]   (+ mode fresh/existing, prochaine étape)
  Profil de stack : ~/.design-to-dev/stack.json (ou variable DESIGN_TO_DEV_STACK), fusionné sur les choix par défaut.
  detect_project.py skills [--require superpowers,security-audit] [--json]
"""
import argparse
import html
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

SKIP_DIRS = {"node_modules", ".git", ".next", ".nuxt", ".svelte-kit", ".turbo", ".cache", "dist", "build",
             "out", "target", "coverage", "__pycache__", ".venv", "venv", ".agents", ".claude", ".codex",
             "Pods", "DerivedData", ".gradle"}
UI_EXT = {".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro", ".swift", ".kt", ".dart"}
TEXT_EXT = UI_EXT | {".js", ".mjs", ".ts", ".css", ".scss", ".json", ".md", ".toml", ".yaml", ".yml",
                     ".xml", ".plist", ".gradle", ".kts", ".rs", ".sql"}
MAX_READ = 512 * 1024

# --------------------------------------------------------------------------- intention

INTENTS = {
    "vitrine": "Site vitrine / landing page",
    "dashboard": "Dashboard web (connexion admin / utilisateur)",
    "desktop": "Application desktop (.exe / .dmg)",
    "ios": "Application iOS / macOS",
    "android": "Application Android",
    "backend": "API backend",
}
STACKS = {
    "vitrine": "Astro + Tailwind CSS + Motion/GSAP (îlots Svelte ou React) ; Rust Axum si routes dynamiques",
    "dashboard": "SvelteKit (ou Next.js) + TanStack Query + shadcn/ui + Tailwind ; Rust Axum + SQLx + PostgreSQL",
    "desktop": "Tauri 2 (backend Rust, UI Svelte/React) + SQLite (rusqlite/sqlx) + keyring",
    "ios": "Swift + SwiftUI + SwiftData + Keychain ; cœur Rust partagé via UniFFI",
    "android": "Kotlin + Jetpack Compose + Room/DataStore + Android Keystore ; cœur Rust via UniFFI",
    "backend": "Rust Axum + Tower + SQLx + PostgreSQL + Redis/Valkey",
}
# (motif, poids) cherchés dans les noms de fichiers et le texte des écrans
SIGNALS = {
    "vitrine": [(r"\bhero\b", 3), (r"\blanding\b", 3), (r"\bpricing\b|\btarifs?\b", 2), (r"testimonial|t[ée]moignage", 2),
                (r"\bfaq\b", 1), (r"\bnewsletter\b", 2), (r"\bcta\b|call[- ]to[- ]action", 1), (r"\bportfolio\b", 2),
                (r"\babout\b|[àa] propos", 1), (r"\bfeatures?\b|fonctionnalit[ée]s", 1)],
    "dashboard": [(r"\bdashboard\b|tableau de bord", 3), (r"\badmin\b", 3), (r"\bsidebar\b", 2),
                  (r"\b(log ?in|sign ?in|connexion|se connecter)\b", 2), (r"\bkpi\b|analytics|statisti", 2),
                  (r"\b(recharts|echarts|chart\.js|apexcharts)\b", 3), (r"<table\b|datatable|data-table", 2),
                  (r"\b(users|utilisateurs|r[ôo]les?|permissions)\b", 1), (r"\b(logout|d[ée]connexion)\b", 2),
                  (r"\b(settings|param[èe]tres)\b", 1)],
    "desktop": [(r"tauri\.conf|src-tauri|@tauri-apps", 6), (r"\belectron\b", 5), (r"-webkit-app-region", 4),
                (r"title-?bar|window-controls|traffic-lights", 3), (r"\b(minimi[sz]e|maximi[sz]e)\b", 2),
                (r"\b(desktop|\.exe|\.dmg|windows app|macos app)\b", 2)],
    "ios": [(r"\.xcodeproj|\bswiftui\b|import swiftui", 6), (r"\b(iphone|ipad|ios)\b", 3), (r"dynamic[- ]island", 3),
            (r"safe-area-inset|status-?bar|home-indicator", 2), (r"\b(390|393|430)\s*[x×]\s*(844|852|932)\b", 3),
            (r"\bcupertino\b|sf pro", 2), (r"\btab-?bar\b", 1)],
    "android": [(r"androidmanifest|build\.gradle|\bjetpack compose\b|androidx\.compose", 6), (r"\bandroid\b", 3), (r"material ?(3|you)", 2),
                (r"\b(360|412)\s*[x×]\s*(800|915|892)\b", 3), (r"\bfab\b|floating action|bottom-?nav", 1)],
    "backend": [(r"cargo\.toml|\baxum\b|actix", 4), (r"openapi|swagger", 4), (r"migrations?/|\.sql\b", 2),
                (r"\b(api|endpoint|webhook)s?\b", 1)],
}
SIGNAL_RE = {k: [(re.compile(p, re.I), w) for p, w in v] for k, v in SIGNALS.items()}
QUESTIONS = {
    "vitrine": "Le site doit-il avoir des parties dynamiques (formulaire de contact, blog, espace client) ?",
    "dashboard": "Qui se connecte (admin seul, admin + utilisateurs) ? MFA obligatoire ?",
    "desktop": "Cibles : Windows (.exe), macOS (.dmg), Linux ? Données locales seulement ou synchronisées ?",
    "ios": "iPhone seul ou aussi iPad / macOS ? Hors-ligne nécessaire ?",
    "android": "Version Android minimale ? Application liée au même backend que le web ?",
    "backend": "Le backend sert-il plusieurs clients (web + mobile + desktop) ?",
}

# --------------------------------------------------------------------------- écrans

DEMO_RE = re.compile(r"(demo|d[ée]mo|prototype|proto|mock(up)?|maquette|preview|example|exemple|sandbox|playground)", re.I)
PAGE_DIR_RE = re.compile(r"(^|/)(pages|routes|app|screens|views|ecrans|écrans)(/|$)", re.I)
PAGE_NAME_RE = re.compile(r"(page|screen|view|ecran|écran)$", re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
FORM_RE = re.compile(r"<form\b", re.I)
INPUT_RE = re.compile(r"<(?:input|Input|TextField|textarea|select)\b([^>]*)>", re.S)
ATTR_RE = {a: re.compile(a + r"""\s*=\s*["'{]([^"'}]+)""", re.I) for a in ("type", "name", "id", "placeholder")}
TH_RE = re.compile(r"<th\b[^>]*>(.*?)</th>", re.I | re.S)
FETCH_RE = re.compile(r"""\b(?:fetch|axios\.(?:get|post|put|patch|delete)|\$fetch|useQuery|createQuery)\s*\(\s*[`"']?([^`"',)\s]*)""")
# nom explicitement factice, ou nom d'entité seulement s'il est suivi d'un tableau d'objets (`users = [{`)
MOCK_RE = re.compile(r"""\b(?:const|let|var)\s+(\w*(?:mock|fake|sample|dummy|demo|seed|fixture|placeholder)\w*|"""
                     r"""\w*(?:users|orders|products|clients|customers|rows|transactions|invoices)\w*"""
                     r"""(?=\s*(?::[^=]+)?=\s*\[\s*\{))\s*(?::[^=]+)?=\s*\[""", re.I)
FEATURES = {
    "auth": re.compile(r"type\s*=\s*[\"']password|mot de passe|password|sign ?in|log ?in|connexion", re.I),
    "signup": re.compile(r"sign ?up|register|inscription|cr[ée]er un compte", re.I),
    "mfa": re.compile(r"\b(otp|2fa|totp|mfa|code de v[ée]rification|authenticator)\b", re.I),
    "admin": re.compile(r"\badmin", re.I),
    "chart": re.compile(r"<canvas|<svg[^>]*chart|recharts|echarts|chart\.js|apexcharts|\bchart\b", re.I),
    "table": re.compile(r"<table\b|datatable|data-table|<DataGrid", re.I),
    "upload": re.compile(r"type\s*=\s*[\"']file|upload|t[ée]l[ée]vers", re.I),
    "payment": re.compile(r"checkout|paiement|payment|stripe|card number|num[ée]ro de carte", re.I),
    "contact": re.compile(r"contact|newsletter", re.I),
    "search": re.compile(r"type\s*=\s*[\"']search|recherche|search", re.I),
    "settings": re.compile(r"settings|param[èe]tres|profil|profile", re.I),
}


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            yield Path(dirpath) / name


def read_text(path):
    try:
        with open(path, "rb") as f:
            data = f.read(MAX_READ)
    except OSError:
        return ""
    return data.decode("utf-8", errors="replace")


def clean(text, limit=80):
    text = html.unescape(TAG_RE.sub(" ", text))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def slug(text):
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text[:40] or "element"


def screen_kind(rel, text):
    stem = Path(rel).stem
    if DEMO_RE.search(rel):
        return "demo"
    if Path(rel).suffix in (".html", ".htm"):
        return "page" if re.search(r"<(html|body)\b", text, re.I) else "fragment"
    if PAGE_DIR_RE.search(rel) or PAGE_NAME_RE.search(stem) or stem in ("+page", "index", "page"):
        return "page"
    return "component"


def analyse_screen(rel, text):
    title = TITLE_RE.search(text) or H1_RE.search(text)
    fields = []
    for attrs in INPUT_RE.findall(text):
        field = {a: (r.search(attrs).group(1) if r.search(attrs) else None) for a, r in ATTR_RE.items()}
        label = field["name"] or field["id"] or field["placeholder"]
        if label:
            fields.append({"name": clean(label, 40), "type": (field["type"] or "text").lower()})
    columns = [c for c in (clean(h, 40) for h in TH_RE.findall(text)) if c]
    calls = [u for u in FETCH_RE.findall(text) if u]
    mocks = sorted(set(MOCK_RE.findall(text)))
    status = "wired" if any(u.startswith(("/", "http")) or "api" in u for u in calls) else \
        "mock-data" if mocks else "static"
    return {
        "path": rel,
        "kind": screen_kind(rel, text),
        "title": clean(title.group(1)) if title else (PAGE_NAME_RE.sub("", Path(rel).stem) or Path(rel).stem),
        "features": sorted(k for k, r in FEATURES.items() if r.search(text)),
        "forms": len(FORM_RE.findall(text)),
        "fields": fields[:30],
        "table_columns": columns[:30],
        "api_calls": calls[:20],
        "mock_data": mocks[:20],
        "status": status,
    }


def detect_frameworks(root):
    found = set()
    for pkg in [p for p in walk(root) if p.name == "package.json"][:20]:
        try:
            data = json.loads(read_text(pkg))
        except ValueError:
            continue
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        for dep, name in (("react", "react"), ("next", "next"), ("svelte", "svelte"), ("@sveltejs/kit", "sveltekit"),
                          ("astro", "astro"), ("vue", "vue"), ("nuxt", "nuxt"), ("tailwindcss", "tailwind"),
                          ("@tauri-apps/api", "tauri"), ("electron", "electron"), ("motion", "motion"),
                          ("framer-motion", "framer-motion"), ("gsap", "gsap"), ("@tanstack/react-query", "tanstack-query"),
                          ("@tanstack/svelte-query", "tanstack-query"), ("recharts", "recharts"), ("echarts", "echarts"),
                          ("@supabase/supabase-js", "supabase"), ("vite", "vite")):
            if dep in deps:
                found.add(name)
    for p in walk(root):
        n = p.name.lower()
        if n == "cargo.toml":
            t = read_text(p).lower()
            found |= {x for x in ("axum", "actix-web", "tauri", "sqlx", "rusqlite", "uniffi") if x in t}
        elif n.endswith(".swift") or any(part.lower().endswith(".xcodeproj") for part in p.relative_to(root).parts):
            found.add("swift")
        elif n in ("build.gradle", "build.gradle.kts", "androidmanifest.xml"):
            found.add("android")
        elif n == "pubspec.yaml":
            found.add("flutter")
    return sorted(found)


# (dépendance, nom) d'un backend déjà en place, à garder plutôt que remplacer
BACKEND_DEPS = (("@supabase/supabase-js", "Supabase"), ("@supabase/ssr", "Supabase"), ("firebase", "Firebase"),
                ("firebase-admin", "Firebase"), ("@prisma/client", "Prisma"), ("drizzle-orm", "Drizzle"),
                ("express", "Express"), ("@nestjs/core", "NestJS"), ("fastify", "Fastify"), ("hono", "Hono"),
                ("convex", "Convex"), ("@trpc/server", "tRPC"), ("pocketbase", "PocketBase"), ("appwrite", "Appwrite"))
TEXT_BACKENDS = {"pyproject.toml": (("fastapi", "FastAPI"), ("django", "Django"), ("flask", "Flask")),
                 "requirements.txt": (("fastapi", "FastAPI"), ("django", "Django"), ("flask", "Flask")),
                 "gemfile": (("rails", "Rails"),), "composer.json": (("laravel/framework", "Laravel"),),
                 "cargo.toml": (("axum", "Rust Axum"), ("actix-web", "Rust Actix"))}


def detect_backend(root):
    found = set()
    for p in walk(root):
        n = p.name.lower()
        if n == "package.json":
            try:
                data = json.loads(read_text(p))
            except ValueError:
                continue
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            found |= {name for dep, name in BACKEND_DEPS if dep in deps}
        elif n in TEXT_BACKENDS:
            text = read_text(p).lower()
            found |= {name for key, name in TEXT_BACKENDS[n]
                      if re.search(r"(?<![\w-])" + re.escape(key) + r"(?![\w-])", text)}
    return sorted(found)


def load_stack_profile():
    """Profil utilisateur {"stacks": {...}, "first_step": {...}} ; absent = choix par défaut."""
    path = Path(os.environ.get("DESIGN_TO_DEV_STACK") or Path.home() / ".design-to-dev" / "stack.json")
    empty = {"path": None, "stacks": {}, "first_step": {}}
    if not path.is_file():
        return empty
    try:
        data = json.loads(read_text(path))
    except ValueError as e:
        print(f"Profil de stack illisible ({path}) : {e} — choix par défaut utilisés", file=sys.stderr)
        return empty
    return {"path": str(path), "stacks": data.get("stacks") or {}, "first_step": data.get("first_step") or {}}


class _Keep(dict):
    """format_map qui laisse intacts les {champs} inconnus d'un profil utilisateur."""
    def __missing__(self, key):
        return "{" + key + "}"


# --------------------------------------------------------------------------- projet déjà avancé

MANIFESTS = {"package.json": "node", "Cargo.toml": "rust", "pyproject.toml": "python", "requirements.txt": "python",
             "go.mod": "go", "pubspec.yaml": "flutter", "build.gradle": "android", "build.gradle.kts": "android",
             "Package.swift": "swift", "composer.json": "php", "Gemfile": "ruby"}
CODE_DIRS = ("src", "app", "apps", "packages", "web", "api", "server", "lib", "src-tauri", "ios", "android", "core",
             "bin", "cmd", "pkg", "scripts", "tests")
CODE_EXT = UI_EXT | {".js", ".mjs", ".ts", ".rs", ".py", ".go", ".java", ".rb", ".php"}
LOCKFILES = (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"), ("bun.lockb", "bun"), ("bun.lock", "bun"),
             ("package-lock.json", "npm"))


# livrables design-to-dev : un projet à moitié fait ne regénère que ceux qui manquent (mode « compléter »)
DELIVERABLES = {
    "memory": ("mémoire `.agents/memory/etat.md`", [".agents/memory/etat.md"]),
    "agents": ("`AGENTS.md`", ["AGENTS.md"]),
    "screens": ("écrans `docs/design/screens.md`", ["docs/design/screens.md"]),
    "stack": ("stack `docs/architecture/stack.md`", ["docs/architecture/stack.md"]),
    "foundations": ("fondations `docs/security/fondations.md`", ["docs/security/fondations.md"]),
    "requirements": ("exigences `docs/security/exigences.md`", ["docs/security/exigences.md"]),
    "plan": ("plan `docs/superpowers/plans/`", ["docs/superpowers/plans", "docs/plans"]),
    "file_map": ("carte `docs/cleanup/file-map.json`", ["docs/cleanup/file-map.json"]),
}


def deliverables(root):
    found = {}
    for key, (_, rels) in DELIVERABLES.items():
        found[key] = next((r for r in rels if (root / r).is_file()
                           or ((root / r).is_dir() and any((root / r).iterdir()))), None)
    return found


def has_code(folder):
    return any(p.suffix.lower() in CODE_EXT for _, p in zip(range(2000), walk(folder)))


def commands(root, manifests):
    """Commandes install / lancer / tester, lues dans les manifestes (jamais exécutées)."""
    cmds = {}
    if "package.json" in manifests:
        pm = next((m for f, m in LOCKFILES if (root / f).exists()), "npm")
        try:
            scripts = json.loads(read_text(root / "package.json")).get("scripts", {}) or {}
        except ValueError:
            scripts = {}
        cmds["install"] = f"{pm} install"
        run = next((s for s in ("dev", "start", "serve", "preview") if s in scripts), None)
        if run:
            cmds["run"] = f"{pm} run {run}"
        if "test" in scripts:
            cmds["test"] = f"{pm} test"
        if "build" in scripts:
            cmds["build"] = f"{pm} run build"
    if "Cargo.toml" in manifests:
        cmds.setdefault("install", "cargo build")
        cmds.setdefault("run", "cargo run")
        cmds.setdefault("test", "cargo test")
    if "go.mod" in manifests:
        cmds.setdefault("run", "go run .")
        cmds.setdefault("test", "go test ./...")
    if {"pyproject.toml", "requirements.txt"} & set(manifests):
        cmds.setdefault("install", "pip install -e ." if "pyproject.toml" in manifests else "pip install -r requirements.txt")
        cmds.setdefault("test", "pytest")
    if "pubspec.yaml" in manifests:
        cmds.setdefault("install", "flutter pub get")
        cmds.setdefault("run", "flutter run")
        cmds.setdefault("test", "flutter test")
    return cmds


def project_state(root):
    """fresh = export de design à structurer ; existing = projet déjà commencé à compléter (pas à refaire)."""
    manifests = [m for m in MANIFESTS if (root / m).is_file()]
    xcode = sorted(p.name for p in root.glob("*.xcodeproj"))
    code_dirs = [d for d in CODE_DIRS if (root / d).is_dir() and has_code(root / d)]
    signals = manifests + xcode + [f"{d}/" for d in code_dirs]
    if (root / ".git").exists():
        signals.append(".git")
    memory = (root / ".agents" / "memory").is_dir()
    if memory:
        signals.append(".agents/memory")
    lockfile = any((root / f).exists() for f, _ in LOCKFILES) or (root / "Cargo.lock").exists()
    if lockfile:
        signals.append("lockfile")
    existing = (bool(manifests or xcode) and bool(code_dirs or lockfile or memory)) or len(code_dirs) >= 2
    done = deliverables(root)
    return {
        "mode": "existing" if existing else "fresh",
        "signals": signals,
        "manifests": manifests + xcode,
        "code_dirs": code_dirs,
        "git": (root / ".git").exists(),
        "agents_memory": memory,
        "commands": commands(root, manifests),
        "deliverables": done,
        "missing": [k for k, v in done.items() if not v],
    }


FIRST_STEP = {
    "vitrine": "Initialiser Astro + Tailwind dans `site/`, convertir les tokens du design system en "
               "`site/src/styles/tokens.css`, puis porter {screen} en `site/src/pages/index.astro`",
    "dashboard": "Créer `web/` (SvelteKit + Tailwind) et `api/` (Rust Axum + SQLx), brancher les tokens dans "
                 "`web/src/app.css`, puis porter {screen} en {route}",
    "desktop": "Initialiser Tauri 2 dans `app/` (`npm create tauri-app@latest`), brancher les tokens, "
               "puis porter {screen} dans `app/src/`",
    "ios": "Créer le projet Xcode SwiftUI dans `ios/`, traduire les tokens en `Theme.swift`, puis porter {screen} "
           "en première vue SwiftUI",
    "android": "Créer le projet Jetpack Compose dans `android/`, traduire les tokens en `Theme.kt`, puis porter "
               "{screen} en premier écran Compose",
    "backend": "Initialiser `api/` (Rust Axum + SQLx + PostgreSQL), écrire la première migration et l'endpoint {endpoint}",
}


def endpoint_for(screen, contract):
    if set(screen["features"]) & {"auth", "signup"} and contract["auth"]:
        return "POST /api/auth/login"
    if screen["table_columns"]:
        return f"GET /api/{slug(screen['title'])}"
    return contract["endpoints"][0] if contract["endpoints"] else None


KEEP_BACKEND_STEP = ("Garder {backend} déjà en place (pas de nouveau backend) : brancher les tokens dans le frontend "
                     "({front}), puis porter {screen} en le reliant à {backend} pour {endpoint}")


def next_step(state, intent, frameworks, screens, contract, backend=(), first_steps=FIRST_STEP):
    """Action précise par laquelle commencer, écrite dans .agents/memory/etat.md."""
    views = [s for s in screens if s["kind"] in ("page", "demo")]
    auth = next((s for s in views if "auth" in s["features"]), None)
    first = auth or next((s for s in views if s["kind"] == "page"), None) or (views[0] if views else None)
    if state["mode"] == "existing":
        start = state["commands"].get("run")
        prefix = (f"Lancer le projet existant (`{start}`) et vérifier qu'il démarre, puis " if start else
                  "Vérifier que le projet existant compile, puis ")
        mock = next((s for s in views if s["status"] == "mock-data"), None)
        target = mock or (auth if auth and auth["status"] != "wired" else None)
        endpoint = endpoint_for(target, contract) if target else None
        if endpoint:
            return prefix + f"remplacer les données factices de `{target['path']}` par l'appel `{endpoint}`"
        return prefix + "reprendre la première tâche ouverte du plan (`docs/superpowers/plans/`)"
    if intent["ambiguous"] or not intent["primary"]:
        return ("Confirmer ce que tu construis (site vitrine, dashboard, desktop, iOS, Android), "
                "puis relancer `detect_project.py scan` pour fixer la stack")
    screen = f"`{first['path']}`" if first else "le premier écran du design"
    route = "`web/src/routes/(auth)/login`" if auth else "première route de `web/src/routes/`"
    endpoint = (endpoint_for(first, contract) if first else None) or \
        (contract["endpoints"][0] if contract["endpoints"] else "GET /api/health")
    kept = [f for f in frameworks if f in ("react", "next", "svelte", "sveltekit", "vue", "nuxt", "astro")]
    if backend and intent["primary"] in ("dashboard", "backend"):
        return KEEP_BACKEND_STEP.format(backend=", ".join(backend), front=", ".join(kept) or "celui du design",
                                        screen=screen, endpoint=f"`{endpoint}`")
    step = first_steps[intent["primary"]].format_map(_Keep(screen=screen, route=route, endpoint=f"`{endpoint}`"))
    if kept:
        step += f" (ou garder {', '.join(kept)} déjà utilisé par le design — à confirmer)"
    return step


def score_intents(paths, texts):
    scores = Counter()
    evidence = {k: Counter() for k in SIGNALS}
    corpus = [(p, p) for p in paths] + list(texts.items())
    for intent, rules in SIGNAL_RE.items():
        for rx, weight in rules:
            hits = sum(1 for _, t in corpus if rx.search(t))
            if hits:
                scores[intent] += weight * min(hits, 5)
                evidence[intent][rx.pattern] = hits
    return scores, evidence


def decide(scores, screens):
    ranked = [(k, v) for k, v in scores.most_common() if v > 0]
    if not ranked:
        return None, [], True
    best, top = ranked[0]
    # une interface avec connexion ou formulaires de données implique un backend
    needs_backend = any(set(s["features"]) & {"auth", "signup", "upload", "payment"} or s["table_columns"]
                        for s in screens)
    secondary = [k for k, v in ranked[1:] if v >= top * 0.5]
    if needs_backend and "backend" not in secondary and best != "backend":
        secondary.append("backend")
    runner_up = next((v for k, v in ranked[1:] if k != "backend"), 0)
    ambiguous = top < 6 or (best != "backend" and runner_up >= top * 0.75)
    return best, secondary, ambiguous


def backend_contract(screens):
    features = set().union(*(s["features"] for s in screens)) if screens else set()
    entities = {}
    for s in screens:
        if s["table_columns"]:
            entities.setdefault(slug(s["title"]), {"fields": [], "from": []})
            ent = entities[slug(s["title"])]
            ent["fields"] = sorted(set(ent["fields"]) | set(s["table_columns"]))
            ent["from"].append(s["path"])
    endpoints = []
    if "auth" in features:
        endpoints += ["POST /api/auth/login", "POST /api/auth/logout", "POST /api/auth/refresh", "GET /api/me"]
    if "signup" in features:
        endpoints.append("POST /api/auth/register")
    if "mfa" in features:
        endpoints += ["POST /api/auth/mfa/setup", "POST /api/auth/mfa/verify"]
    for name in entities:
        endpoints += [f"GET /api/{name}", f"POST /api/{name}", f"PATCH /api/{name}/:id", f"DELETE /api/{name}/:id"]
    for s in screens:
        if s["forms"] and not set(s["features"]) & {"auth", "signup"} and not s["table_columns"]:
            endpoints.append(f"POST /api/{slug(s['title'])}")
    return {
        "auth": "auth" in features,
        "roles": ["admin", "user"] if "admin" in features and "auth" in features else [],
        "mfa": "mfa" in features,
        "uploads": "upload" in features,
        "payments": "payment" in features,
        "entities": entities,
        "endpoints": sorted(set(endpoints)),
    }


def analyse(root):
    """Analyse complète, sans rien écrire ni afficher (utilisée aussi par scaffold_memory.py)."""
    root = Path(root).resolve()
    paths, texts, screens = [], {}, []
    for p in walk(root):
        rel = p.relative_to(root).as_posix()
        paths.append(rel)
        if p.suffix.lower() in TEXT_EXT:
            texts[rel] = read_text(p)
        if p.suffix.lower() in UI_EXT and rel in texts:
            screens.append(analyse_screen(rel, texts[rel]))
    scores, evidence = score_intents(paths, texts)
    best, secondary, ambiguous = decide(scores, screens)
    intents = [best] + secondary if best else []
    frameworks = detect_frameworks(root)
    backend = detect_backend(root)
    profile = load_stack_profile()
    stacks = {**STACKS, **profile["stacks"]}
    state = project_state(root)
    contract = backend_contract([s for s in screens if s["kind"] != "component"] or screens)
    result = {
        "root": str(root),
        "project": state,
        "frameworks": frameworks,
        "intent": {
            "primary": best,
            "secondary": secondary,
            "ambiguous": ambiguous,
            "scores": dict(scores.most_common()),
            "evidence": {k: dict(v.most_common(5)) for k, v in evidence.items() if v},
            "questions": [QUESTIONS[i] for i in intents] if not ambiguous else
                         ["Que veux-tu construire : site vitrine, dashboard web, app desktop, iOS, Android ?"] +
                         [QUESTIONS[i] for i in intents[:2]],
        },
        "stack_profile": profile["path"],
        "existing_backend": backend,
        "recommended_stack": {i: (f"Garder {', '.join(backend)} (déjà en place) — alternative : {stacks[i]}"
                                  if backend and i in ("dashboard", "backend") else stacks[i]) for i in intents},
        "screens": screens,
        "backend_contract": contract,
    }
    result["next_step"] = next_step(state, result["intent"], frameworks, screens, contract, backend,
                                    {**FIRST_STEP, **profile["first_step"]})
    return result


def scan(root, out):
    if not Path(root).is_dir():
        sys.exit(f"Dossier introuvable : {Path(root).resolve()}")
    result = analyse(root)
    if out:
        Path(out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print_summary(result, out)
    return result


def print_summary(r, out):
    it = r["intent"]
    st = r["project"]
    label = INTENTS.get(it["primary"], "indéterminée")
    if st["mode"] == "existing":
        print(f"Projet DÉJÀ COMMENCÉ ({', '.join(st['signals'])}) → mode « nettoyer + compléter l'infra agents », "
              "pas de restructuration")
    else:
        print("Export de design à structurer (mode fresh)")
    print(f"Intention : {label}" + (" (AMBIGUË — poser les questions)" if it["ambiguous"] else ""))
    if it["secondary"]:
        print("  + " + ", ".join(INTENTS[i] for i in it["secondary"]))
    print("Scores : " + (", ".join(f"{k}={v}" for k, v in it["scores"].items()) or "aucun signal"))
    print("Frameworks déjà présents : " + (", ".join(r["frameworks"]) or "aucun"))
    if r["existing_backend"]:
        print(f"Backend déjà en place : {', '.join(r['existing_backend'])} → à garder (pas de nouveau backend)")
    print("Profil de stack : " + (r["stack_profile"] or "défaut (~/.design-to-dev/stack.json absent)"))
    for i, s in r["recommended_stack"].items():
        print(f"  stack {i} : {s}")
    have = [DELIVERABLES[k][0] for k, v in st["deliverables"].items() if v]
    if have:
        print("Déjà en place : " + ", ".join(have))
        print("Manque (mode compléter) : " + (", ".join(DELIVERABLES[k][0] for k in st["missing"]) or "rien"))
    kinds = Counter(s["kind"] for s in r["screens"])
    status = Counter(s["status"] for s in r["screens"] if s["kind"] != "component")
    print(f"Écrans existants : {kinds.get('page', 0)} pages, {kinds.get('demo', 0)} démos, "
          f"{kinds.get('fragment', 0)} fragments, {kinds.get('component', 0)} composants")
    print("  état : " + (", ".join(f"{k}={v}" for k, v in status.items()) or "—"))
    for s in [s for s in r["screens"] if s["kind"] in ("page", "demo")][:15]:
        print(f"  - [{s['kind']}] {s['path']} — {s['title']} {s['features'] or ''}")
    bc = r["backend_contract"]
    print(f"Backend à brancher : auth={bc['auth']} roles={bc['roles'] or '-'} mfa={bc['mfa']} "
          f"entités={list(bc['entities']) or '-'} ({len(bc['endpoints'])} endpoints)")
    for q in it["questions"]:
        print(f"  ? {q}")
    print(f"Prochaine étape : {r['next_step']}")
    if out:
        print(f"→ {out}")


# --------------------------------------------------------------------------- skills compagnes

COMPANIONS = {
    "superpowers": {
        "skills": ["brainstorming", "writing-plans"],
        "install": {
            "claude": "/plugin install superpowers@claude-plugins-official",
            "codex": "Codex app : Plugins → superpowers → Install Plugin",
            "gemini": "gemini extensions install https://github.com/obra/superpowers",
        },
        "repo": "https://github.com/obra/superpowers",
    },
    "security-audit": {
        "skills": ["security-audit"],
        "install": {"all": "npx skills add https://github.com/cloudflare/security-audit-skill --skill security-audit --global",
                    "projet": "npx design-to-dev security-kit install . (copie épinglée et scannée dans .claude/skills)"},
        "repo": "https://github.com/cloudflare/security-audit-skill",
    },
}
NAME_RE = re.compile(r"^name:\s*['\"]?([\w:.-]+)", re.M)


def skill_roots():
    home = Path.home()
    claude = Path(os.environ.get("CLAUDE_CONFIG_DIR") or home / ".claude")
    codex = Path(os.environ.get("CODEX_HOME") or home / ".codex")
    roots = [claude / "skills", home / ".agents" / "skills", codex / "skills", Path.cwd() / ".claude" / "skills",
             Path.cwd() / ".agents" / "skills", home / ".gemini" / "extensions"]
    roots += [claude / "plugins" / "cache", codex / "plugins", codex / ".tmp" / "plugins"]
    return [r for r in roots if r.is_dir()]


def installed_skills():
    found = {}
    for root in skill_roots():
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            if dirpath.count(os.sep) - str(root).count(os.sep) > 7:
                dirnames[:] = []
            if "SKILL.md" in filenames:
                m = NAME_RE.search(read_text(Path(dirpath) / "SKILL.md")[:2000])
                name = m.group(1).split(":")[-1] if m else Path(dirpath).name
                found.setdefault(name, []).append(dirpath)
    return found


def skills(require, as_json):
    have = installed_skills()
    report = {}
    for comp, cfg in COMPANIONS.items():
        missing = [s for s in cfg["skills"] if s not in have]
        report[comp] = {"installed": not missing, "missing": missing,
                        "paths": {s: have[s][0] for s in cfg["skills"] if s in have},
                        "install": cfg["install"], "repo": cfg["repo"]}
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for comp, r in report.items():
            print(f"{comp:15} {'installée' if r['installed'] else 'ABSENTE (' + ', '.join(r['missing']) + ')'}")
            for s, p in r["paths"].items():
                print(f"  {s}: {p}")
            if not r["installed"]:
                for agent, cmd in r["install"].items():
                    print(f"  installer ({agent}) : {cmd}")
    wanted = [c.strip() for c in (require or "").split(",") if c.strip()]
    return 1 if any(not report.get(c, {}).get("installed") for c in wanted) else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("scan")
    a.add_argument("folder")
    a.add_argument("--out")
    b = sub.add_parser("skills")
    b.add_argument("--require")
    b.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.cmd == "scan":
        scan(args.folder, args.out)
        return 0
    return skills(args.require, args.json)


if __name__ == "__main__":
    sys.exit(main())
