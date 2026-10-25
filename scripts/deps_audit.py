"""design-to-dev : inventaire des dépendances, runtimes et API externes, failles connues (appelé par foundations / deps).

Sans `--online`, rien ne sort de la machine : l'inventaire est dressé, comparé à la base hors ligne, et marqué
« non vérifié en ligne ». Avec `--online` (accord de l'utilisateur), seuls des noms et versions de paquets publics
partent vers OSV.dev (failles et historique), les registres publics (dernière version stable, dépréciation) et
endoflife.date (support des runtimes et frameworks). Aucun fichier, chemin ou secret n'est transmis.
Les réponses sont des données : jamais exécutées, jamais suivies.
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

OK, WARN, BLOCK = "✅", "⚠️", "❌"
USER_AGENT = "design-to-dev (+https://github.com/duckysface/design-to-dev)"
TIMEOUT, MAX_BODY, MAX_QUERY, MAX_DETAILS, MAX_DIRECT = 15, 8 * 1024 * 1024, 3000, 300, 150
BASE_ENV = "DESIGN_TO_DEV_ADVISORY_BASE"  # tests : remplace tous les services par un serveur local
LOCAL = {"127.0.0.1", "localhost", "::1"}
HOSTS = {
    "osv": "https://api.osv.dev", "eol": "https://endoflife.date/api", "npm": "https://registry.npmjs.org",
    "PyPI": "https://pypi.org/pypi", "crates.io": "https://crates.io/api/v1/crates",
    "Packagist": "https://repo.packagist.org/p2", "Go": "https://proxy.golang.org",
    "RubyGems": "https://rubygems.org/api/v1/gems", "Pub": "https://pub.dev/api/packages",
}
ID_RE = re.compile(r"[A-Za-z0-9._:-]{3,80}")
NAME_RE = re.compile(r"[@A-Za-z0-9._/~-]{1,214}")
CDN_NPM = {"angularjs": "angular", "twitter-bootstrap": "bootstrap", "jqueryui": "jquery-ui", "chartjs": "chart.js",
           "highlightjs": "highlight.js", "purify": "dompurify"}
# produit endoflife.date suivi pour une dépendance directe (un produit inconnu est ignoré)
FRAMEWORKS = {("npm", "vue"): "vue", ("npm", "@angular/core"): "angular", ("npm", "angular"): "angularjs",
              ("npm", "react"): "react", ("npm", "next"): "nextjs", ("npm", "nuxt"): "nuxt",
              ("npm", "electron"): "electron", ("npm", "jquery"): "jquery", ("npm", "bootstrap"): "bootstrap",
              ("PyPI", "django"): "django", ("Packagist", "laravel/framework"): "laravel",
              ("Packagist", "symfony/http-kernel"): "symfony", ("RubyGems", "rails"): "rails"}
RUNTIME_LABEL = {"nodejs": "Node.js", "php": "PHP", "python": "Python", "ruby": "Ruby", "go": "Go"}
API_RE = re.compile(r"""(?:fetch|axios(?:\.\w+)?|\$http\.\w+|requests\.\w+|http\.\w+|curl_init|baseURL\s*[:=])"""
                    r"""\s*\(?\s*["'`](https?://[A-Za-z0-9.-]+\.[A-Za-z]{2,})""")
API_SKIP = ("localhost", "127.0.0.1", "example.", "w3.org", "schema.org")
CODE_EXT = {".html", ".htm", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".astro", ".py", ".php", ".rb", ".go",
            ".rs", ".dart", ".swift", ".kt"}
DEP_FILES = {"package.json", "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pyproject.toml", "poetry.lock",
             "uv.lock", "pipfile.lock", "cargo.toml", "cargo.lock", "composer.json", "composer.lock", "go.mod",
             "gemfile", "gemfile.lock", "pubspec.lock", ".nvmrc", ".node-version", ".python-version", "runtime.txt",
             ".ruby-version", ".tool-versions"}


def clean(text, n=110):
    text = re.sub(r"[‪-‮⁦-⁩​-‍﻿]", "", str(text or ""))
    text = " ".join(text.replace("|", "/").replace("`", "'").split())
    return text if len(text) <= n else text[:n] + "…"


def vkey(s):
    nums = [int(x) for x in re.findall(r"\d+", str(s or ""))[:4]]
    return tuple(nums + [0] * (4 - len(nums)))


def first_version(spec):
    m = re.search(r"\d+(?:\.\d+){0,3}", str(spec or ""))
    return m.group(0) if m else None


def pkg(eco, name, ver, src, direct=False, exact=True):
    return {"eco": eco, "name": name, "version": ver, "src": src, "direct": direct, "exact": exact}


# ---------------------------------------------------------------- inventaire

def parse_npm(path, rel, text, direct_names):
    out = []
    data = json.loads(text)
    if path.name == "package.json":
        for section in ("dependencies", "devDependencies", "optionalDependencies"):
            for name, spec in (data.get(section) or {}).items():
                direct_names.add(("npm", name))
                if isinstance(spec, str) and not (path.parent / "package-lock.json").is_file() \
                        and not (path.parent / "yarn.lock").is_file():
                    ver = first_version(spec) if not re.match(r"(?:file|git|link|http|workspace):", spec) else None
                    out.append(pkg("npm", name, ver, rel, True, bool(re.fullmatch(r"\d+\.\d+\.\d+", spec))))
        return out
    for key, meta in (data.get("packages") or {}).items():
        name = key.rsplit("node_modules/", 1)[-1]
        if name and isinstance(meta, dict) and not meta.get("link") and re.match(r"\d", str(meta.get("version", ""))):
            out.append(pkg("npm", meta.get("name") or name, meta["version"], rel))
    if not out:  # lockfile v1
        for name, meta in (data.get("dependencies") or {}).items():
            if isinstance(meta, dict) and re.match(r"\d", str(meta.get("version", ""))):
                out.append(pkg("npm", name, meta["version"], rel))
    return out


def parse_yarn(rel, text):
    rx = re.compile(r'^"?(@?[^@\s"]+)@[^\n]*:\n(?:[ \t]+[^\n]*\n)*?[ \t]+version:?\s+"?([\d][^"\s]*)"?', re.M)
    return [pkg("npm", n, v, rel) for n, v in rx.findall(text)]


def parse_python(path, rel, text, direct_names):
    name = path.name.lower()
    if name == "pipfile.lock":
        data = json.loads(text)
        return [pkg("PyPI", n, first_version(m.get("version")), rel, exact=True)
                for sec in ("default", "develop") for n, m in (data.get(sec) or {}).items() if isinstance(m, dict)]
    if name in ("poetry.lock", "uv.lock"):
        rx = re.compile(r'\[\[package\]\]\s+name\s*=\s*"([^"]+)"\s+version\s*=\s*"([^"]+)"')
        return [pkg("PyPI", n, v, rel) for n, v in rx.findall(text)]
    specs = []
    if name == "pyproject.toml":
        for block in re.findall(r"(?:^|\n)\s*(?:dependencies|dev-dependencies|[\w-]+)\s*=\s*\[(.*?)\]", text, re.S):
            specs += re.findall(r'"([A-Za-z0-9][A-Za-z0-9._-]*(?:\[[^\]]*\])?\s*[^"]*)"', block)
        poetry = re.search(r"\[tool\.poetry\.dependencies\](.*?)(?:\n\[|\Z)", text, re.S)
        if poetry:
            specs += [f"{k}{v}" for k, v in re.findall(r'^\s*([A-Za-z0-9._-]+)\s*=\s*"([^"]*)"', poetry.group(1), re.M)
                      if k.lower() != "python"]
    else:  # requirements*.txt
        specs = [ln.split("#")[0].strip() for ln in text.splitlines()]
    out = []
    has_lock = any((path.parent / f).is_file() for f in ("poetry.lock", "uv.lock", "Pipfile.lock"))
    for spec in specs:
        m = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*(===?|>=|~=|\^|~|>)?\s*([\w.*]+)?", spec)
        if not m or spec.startswith(("-", "git+", "http")):
            continue
        n = m.group(1).lower().replace("_", "-")
        direct_names.add(("PyPI", n))
        if not has_lock:
            out.append(pkg("PyPI", n, first_version(m.group(3)), rel, True, m.group(2) in ("==", "===")))
    return out


def parse_cargo(path, rel, text, direct_names):
    if path.name == "Cargo.toml":
        for sec in re.findall(r"\[(?:dev-|build-)?dependencies\](.*?)(?:\n\[|\Z)", text, re.S):
            direct_names.update(("crates.io", k) for k in re.findall(r"^\s*([A-Za-z0-9_-]+)\s*=", sec, re.M))
        return []
    rx = re.compile(r'\[\[package\]\]\s+name\s*=\s*"([^"]+)"\s+version\s*=\s*"([^"]+)"(?:\s+source\s*=\s*"([^"]*)")?')
    return [pkg("crates.io", n, v, rel) for n, v, src in rx.findall(text) if src.startswith("registry+")]


def parse_composer(path, rel, text, direct_names):
    data = json.loads(text)
    if path.name == "composer.json":
        out = []
        for sec in ("require", "require-dev"):
            for n, spec in (data.get(sec) or {}).items():
                if "/" in n:
                    direct_names.add(("Packagist", n.lower()))
                    if not (path.parent / "composer.lock").is_file():
                        out.append(pkg("Packagist", n.lower(), first_version(spec), rel, True, False))
        return out
    return [pkg("Packagist", p["name"].lower(), str(p.get("version", "")).lstrip("v"), rel)
            for sec in ("packages", "packages-dev") for p in data.get(sec) or []
            if isinstance(p, dict) and p.get("name") and re.match(r"v?\d", str(p.get("version", "")))]


def parse_go(rel, text, direct_names):
    out = []
    lines = re.findall(r"^\s*(?:require\s+)?([a-z0-9.-]+\.[a-z]{2,}/[^\s]+)\s+(v\d[^\s]*)(\s*//\s*indirect)?",
                       text, re.M)
    for mod, ver, indirect in lines:
        if not indirect:
            direct_names.add(("Go", mod))
        out.append(pkg("Go", mod, ver.lstrip("v").split("+")[0], rel, not indirect))
    return out


def parse_ruby(path, rel, text, direct_names):
    if path.name == "Gemfile":
        direct_names.update(("RubyGems", n) for n in re.findall(r"""^\s*gem\s+["']([\w.-]+)""", text, re.M))
        return []
    return [pkg("RubyGems", n, v.split("-")[0], rel) for n, v in re.findall(r"^    ([\w.-]+) \(([\d][^)]*)\)$", text, re.M)]


def parse_pub(rel, text):
    rx = re.compile(r'^  ([a-z0-9_]+):\n((?:    .*\n)+)', re.M)
    out = []
    for name, body in rx.findall(text):
        ver = re.search(r'version:\s*"([^"]+)"', body)
        if ver:
            out.append(pkg("Pub", name, ver.group(1), rel, "direct" in body))
    return out


def collect_packages(root, paths, read):
    packages, direct_names, errors = [], set(), []
    for p in paths:
        low, rel = p.name.lower(), p.relative_to(root).as_posix()
        try:
            text = read(p)
            if low in ("package.json", "package-lock.json", "npm-shrinkwrap.json"):
                packages += parse_npm(p, rel, text, direct_names)
            elif low == "yarn.lock":
                packages += parse_yarn(rel, text)
            elif low in ("pyproject.toml", "poetry.lock", "uv.lock", "pipfile.lock") \
                    or re.fullmatch(r"requirements[\w.-]*\.txt", low):
                packages += parse_python(p, rel, text, direct_names)
            elif low in ("cargo.toml", "cargo.lock"):
                packages += parse_cargo(p, rel, text, direct_names)
            elif low in ("composer.json", "composer.lock"):
                packages += parse_composer(p, rel, text, direct_names)
            elif low == "go.mod":
                packages += parse_go(rel, text, direct_names)
            elif low in ("gemfile", "gemfile.lock"):
                packages += parse_ruby(p, rel, text, direct_names)
            elif low == "pubspec.lock":
                packages += parse_pub(rel, text)
        except (ValueError, KeyError, TypeError, AttributeError):
            errors.append(f"`{rel}` illisible : dépendances non inventoriées")
    seen, unique = set(), []
    for d in packages:
        key = (d["eco"], d["name"].lower(), d["version"])
        if key in seen or not NAME_RE.fullmatch(d["name"]):
            continue
        seen.add(key)
        unique.append({**d, "direct": d["direct"] or (d["eco"], d["name"].lower()) in direct_names
                       or (d["eco"], d["name"]) in direct_names})
    return unique, errors


def collect_runtimes(root, paths, read):
    found = []

    def add(product, spec, rel):
        ver = first_version(spec)
        if ver and (product, ver) not in {(f[0], f[1]) for f in found}:
            found.append((product, ver, rel))

    for p in paths:
        low, rel = p.name.lower(), p.relative_to(root).as_posix()
        text = read(p)
        try:
            if low == "package.json":
                add("nodejs", (json.loads(text).get("engines") or {}).get("node"), rel)
            elif low == "composer.json":
                add("php", (json.loads(text).get("require") or {}).get("php"), rel)
        except (ValueError, AttributeError):
            continue
        if low in (".nvmrc", ".node-version"):
            add("nodejs", text.strip(), rel)
        elif low in (".python-version", "runtime.txt"):
            add("python", text.strip(), rel)
        elif low == ".ruby-version":
            add("ruby", text.strip(), rel)
        elif low == "pyproject.toml":
            m = re.search(r'requires-python\s*=\s*"([^"]+)"', text)
            add("python", m and m.group(1), rel)
        elif low == "go.mod":
            m = re.search(r"^go\s+(\d[\d.]*)", text, re.M)
            add("go", m and m.group(1), rel)
        elif low == "gemfile.lock":
            m = re.search(r"RUBY VERSION\s+ruby\s+(\d[\d.]*)", text)
            add("ruby", m and m.group(1), rel)
        elif low == ".tool-versions":
            for tool, ver in re.findall(r"^(nodejs|python|php|ruby|golang)\s+(\S+)", text, re.M):
                add({"golang": "go"}.get(tool, tool), ver, rel)
        elif low.startswith("dockerfile") or low.endswith(".dockerfile"):
            for img, tag in re.findall(r"(?im)^\s*FROM\s+(?:[\w.-]+/)?(node|php|python|ruby|golang):(\d[\w.-]*)", text):
                add({"node": "nodejs", "golang": "go"}.get(img.lower(), img.lower()), tag, rel)
    return found


def collect_apis(root, files):
    hosts = {}
    for p, text in files:
        if p.suffix.lower() not in CODE_EXT:
            continue
        for url in API_RE.findall(text):
            host = urllib.parse.urlparse(url).hostname or ""
            if host and not any(s in host for s in API_SKIP):
                hosts.setdefault(host, p.relative_to(root).as_posix())
    return sorted(hosts.items())[:40]


# ---------------------------------------------------------------- réseau

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed(newurl):
            raise urllib.error.URLError(f"redirection refusée vers {urllib.parse.urlparse(newurl).hostname}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(SafeRedirect)


def allowed(url):
    p = urllib.parse.urlparse(url)
    return p.scheme == "https" or (p.scheme == "http" and p.hostname in LOCAL)


def service(key):
    base = os.environ.get(BASE_ENV)
    if base and allowed(base):
        return base.rstrip("/") + "/" + re.sub(r"[^a-z]", "", key.lower())
    return HOSTS[key]


class Net:
    def __init__(self):
        self.errors = set()

    def get(self, url, payload=None):
        host = urllib.parse.urlparse(url).hostname
        if not allowed(url):
            self.errors.add(f"{host} : URL non HTTPS refusée")
            return None
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if data:
            headers["Content-Type"] = "application/json"
        try:
            with OPENER.open(urllib.request.Request(url, data=data, headers=headers), timeout=TIMEOUT) as r:
                body = r.read(MAX_BODY + 1)
            if len(body) > MAX_BODY:
                raise ValueError("réponse trop volumineuse")
            return json.loads(body.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code != 404:
                self.errors.add(f"{host} : HTTP {e.code}")
        except (urllib.error.URLError, OSError, ValueError) as e:
            self.errors.add(f"{host} : {type(e).__name__}")
        return None


def osv_query(net, queries):
    """Liste de [(id, modifié)] par requête ; None si OSV n'a pas répondu."""
    out = []
    for i in range(0, len(queries), 500):
        chunk = queries[i:i + 500]
        res = net.get(service("osv") + "/v1/querybatch", {"queries": chunk})
        results = res.get("results") if isinstance(res, dict) else None
        if not isinstance(results, list) or len(results) != len(chunk):
            return None
        for r in results:
            vulns = (r or {}).get("vulns") if isinstance(r, dict) else None
            out.append([(v["id"], str(v.get("modified", ""))[:10]) for v in vulns or []
                        if isinstance(v, dict) and ID_RE.fullmatch(str(v.get("id", "")))])
    return out


def osv_query_for(d):
    q = {"package": {"name": d["name"], "ecosystem": d["eco"]}}
    return {**q, "version": d["version"]} if d["version"] else q


def go_escape(module):
    return "".join("!" + c.lower() if c.isupper() else c for c in module)


def latest(net, d):
    """(dernière version stable, avis de dépréciation) selon le registre de l'écosystème."""
    eco, name = d["eco"], d["name"]
    q = urllib.parse.quote
    try:
        if eco == "npm":
            r = net.get(f"{service('npm')}/{q(name, safe='@/')}/latest") or {}
            return r.get("version"), r.get("deprecated")
        if eco == "PyPI":
            info = (net.get(f"{service('PyPI')}/{q(name)}/json") or {}).get("info") or {}
            return info.get("version"), info.get("yanked_reason") if info.get("yanked") else None
        if eco == "crates.io":
            return ((net.get(f"{service('crates.io')}/{q(name)}") or {}).get("crate") or {}).get("max_stable_version"), None
        if eco == "Packagist":
            versions = ((net.get(f"{service('Packagist')}/{q(name, safe='/')}.json") or {}).get("packages") or {}).get(name) or []
            stable = [v for v in versions if isinstance(v, dict)
                      and not re.search(r"(?i)dev|alpha|beta|rc", str(v.get("version", "")))]
            return (str(stable[0]["version"]).lstrip("v") if stable else None), \
                (stable[0].get("abandoned") and f"abandonné ({stable[0]['abandoned']})" if stable else None)
        if eco == "Go":
            return str((net.get(f"{service('Go')}/{q(go_escape(name), safe='/!')}/@latest") or {}).get("Version", "")).lstrip("v") or None, None
        if eco == "RubyGems":
            return (net.get(f"{service('RubyGems')}/{q(name)}.json") or {}).get("version"), None
        if eco == "Pub":
            r = net.get(f"{service('Pub')}/{q(name)}") or {}
            return (r.get("latest") or {}).get("version"), "abandonné" if r.get("isDiscontinued") else None
    except (AttributeError, TypeError, KeyError, IndexError):
        pass
    return None, None


def vuln_detail(net, vid, d):
    data = net.get(f"{service('osv')}/v1/vulns/{urllib.parse.quote(vid)}")
    if not isinstance(data, dict):
        return {"id": vid, "cves": [], "severity": "?", "summary": "détail indisponible", "fixed": None,
                "where": "", "cwe": []}
    sev = (data.get("database_specific") or {}).get("severity")
    fixed, where = [], []
    for aff in data.get("affected") or []:
        if not isinstance(aff, dict) or str((aff.get("package") or {}).get("name", "")).lower() != d["name"].lower():
            continue
        for rng in aff.get("ranges") or []:
            fixed += [ev["fixed"] for ev in rng.get("events") or [] if isinstance(ev, dict) and ev.get("fixed")]
        eco = aff.get("ecosystem_specific") or {}
        where += eco.get("affected_functions") or []
        where += [s for imp in eco.get("imports") or [] for s in imp.get("symbols") or []]
        sev = sev or (aff.get("database_specific") or {}).get("severity")
    cur = vkey(d["version"])
    later = sorted((f for f in fixed if vkey(f) > cur), key=vkey)
    return {"id": vid, "cves": [a for a in data.get("aliases") or [] if str(a).startswith("CVE-")],
            "severity": str(sev or "?").upper(), "summary": clean(data.get("summary") or data.get("details"), 140),
            "fixed": later[0] if later else None, "where": clean(", ".join(map(str, where[:4])), 80),
            "cwe": (data.get("database_specific") or {}).get("cwe_ids") or []}


def eol_status(net, product, ver, cache):
    """(en fin de vie ?, date de fin, version conseillée) d'après endoflife.date ; None si inconnu."""
    if product not in cache:
        cycles = net.get(f"{service('eol')}/{urllib.parse.quote(product)}.json")
        cache[product] = cycles if isinstance(cycles, list) else None
    cycles = cache[product]
    if not cycles:
        return None
    today = time.strftime("%Y-%m-%d")
    match = next((c for c in cycles if isinstance(c, dict)
                  and (ver == str(c.get("cycle")) or ver.startswith(f"{c.get('cycle')}."))), None)
    if not match:
        return None
    eol = match.get("eol")
    ended = eol is True or (isinstance(eol, str) and eol <= today)
    alive = [c for c in cycles if isinstance(c, dict)
             and not (c.get("eol") is True or (isinstance(c.get("eol"), str) and c["eol"] <= today))]
    supported = next((c for c in alive if c.get("lts")), alive[0] if alive else {})  # LTS d'abord
    advice = supported.get("latest") or supported.get("cycle")
    return ended, eol if isinstance(eol, str) else ("terminée" if eol else "non annoncée"), advice


def offline_runtime(table, product, ver):
    rt = table.get(product)
    if not rt:
        return None
    width = len(rt["min_supported"].split("."))
    ended = vkey(".".join(ver.split(".")[:width])) < vkey(rt["min_supported"])
    return ended, f"support minimal {rt['min_supported']}, base hors ligne du {rt.get('checked', '?')}", rt["min_supported"]


# ---------------------------------------------------------------- audit

def audit(root, paths, files, read, cdn, online, libs_data):
    """Retourne le rapport des dépendances ; ne touche au réseau que si `online`."""
    dep_paths = [p for p in paths if p.name.lower() in DEP_FILES or re.fullmatch(r"requirements[\w.-]*\.txt", p.name.lower())
                 or p.name.lower().startswith("dockerfile") or p.name.lower().endswith(".dockerfile")]
    packages, errors = collect_packages(root, dep_paths, read)
    for rel, name, ver in cdn:
        name = CDN_NPM.get(name.lower(), name.lower().removesuffix(".min").removesuffix(".slim"))
        if NAME_RE.fullmatch(name):
            packages.append(pkg("npm", name, ver, rel, True))
    packages = packages[:MAX_QUERY]
    res = {"packages": packages, "runtimes": [], "apis": collect_apis(root, files), "vulns": {}, "history": {},
           "latest": {}, "eol": [], "replace": [], "errors": errors, "online": False, "net_errors": [],
           "notable": {k: v.get("notable") or [] for k, v in (libs_data.get("runtimes") or {}).items()}}
    alternatives = libs_data.get("alternatives") or {}
    for d in packages:
        alt = alternatives.get(f"{d['eco']}:{d['name'].lower()}")
        if alt:
            res["replace"].append((d, alt["why"], alt["replace"]))
    runtimes = collect_runtimes(root, dep_paths, read)
    if not online:
        res["runtimes"] = [(p, v, rel, offline_runtime(libs_data.get("runtimes") or {}, p, v)) for p, v, rel in runtimes]
        return res
    net = Net()
    with_version = [d for d in packages if d["version"]]
    found = osv_query(net, [osv_query_for(d) for d in with_version])
    direct = [d for d in packages if d["direct"]][:MAX_DIRECT]
    history = osv_query(net, [{"package": {"name": d["name"], "ecosystem": d["eco"]}} for d in direct])
    res["online"] = found is not None
    if found is not None:
        ids = {}
        for d, vulns in zip(with_version, found):
            if vulns:
                res["vulns"][id(d)] = [v for v, _ in vulns]
                for v, _ in vulns:
                    ids.setdefault(v, d)
        with ThreadPoolExecutor(max_workers=8) as pool:
            details = dict(zip(list(ids)[:MAX_DETAILS], pool.map(lambda v: vuln_detail(net, v, ids[v]), list(ids)[:MAX_DETAILS])))
        res["vulns"] = {k: [details.get(v) or {"id": v, "cves": [], "severity": "?", "summary": "non détaillé (limite)",
                                               "fixed": None, "where": "", "cwe": []} for v in vs]
                        for k, vs in res["vulns"].items()}
    if history is not None:
        res["history"] = {id(d): (len(h), max((m for _, m in h), default="")) for d, h in zip(direct, history)}
    with ThreadPoolExecutor(max_workers=8) as pool:
        res["latest"] = dict(zip((id(d) for d in direct), pool.map(lambda d: latest(net, d), direct)))
    cache = {}
    res["runtimes"] = [(p, v, rel, eol_status(net, p, v, cache) or offline_runtime(libs_data.get("runtimes") or {}, p, v))
                       for p, v, rel in runtimes]
    for d in direct:
        product = FRAMEWORKS.get((d["eco"], d["name"].lower()))
        st = product and d["version"] and eol_status(net, product, d["version"], cache)
        if st:
            res["eol"].append((d, product, st))
    res["net_errors"] = sorted(net.errors)
    return res


def label(d):
    return f"{d['name']} {d['version'] or '(version non figée)'}" + ("" if d["exact"] else " (borne minimale)")


def items(res):
    """Lignes ❌/⚠️ pour fondations.md : (niveau, contrôle, texte)."""
    out = []
    by_id = {id(d): d for d in res["packages"]}
    for key, vulns in res["vulns"].items():
        d = by_id[key]
        ids = [v["cves"][0] if v["cves"] else v["id"] for v in vulns]
        no_fix = [i for i, v in zip(ids, vulns) if not v["fixed"]]
        malware = [v["id"] for v in vulns if v["id"].startswith("MAL-")]
        sev = sorted({v["severity"] for v in vulns} - {"?"})
        fix = max((v["fixed"] for v in vulns if v["fixed"]), key=vkey, default=None)
        head = f"`{d['src']}` : {label(d)} — {len(vulns)} faille(s) connue(s) ({', '.join(ids[:4])}" \
               f"{' …' if len(ids) > 4 else ''}{'; gravité ' + '/'.join(sev) if sev else ''})"
        if malware:
            out.append((BLOCK, "vuln", f"{head} — **paquet malveillant connu** : le retirer, vérifier les machines qui "
                                       "l'ont installé, changer les secrets exposés"))
        elif no_fix:
            out.append((BLOCK, "vuln", f"{head} — aucun correctif publié pour {', '.join(no_fix[:3])} : choisir une "
                                       "alternative ou isoler la partie touchée (voir dependances.md)"))
        elif "CRITICAL" in sev:
            out.append((BLOCK, "vuln", f"{head} → passer à {fix} au minimum avant tout code"))
        else:
            out.append((WARN, "vuln", f"{head} → passer à {fix} au minimum"))
    for d, why, repl in res["replace"]:
        out.append((WARN, "deps", f"`{d['src']}` : {d['name']} — {why} → {repl}"))
    replaced = {id(d) for d, _, _ in res["replace"]}
    for key, (ver, deprecated) in res["latest"].items():
        if deprecated and key not in replaced:
            d = by_id[key]
            out.append((WARN, "deps", f"`{d['src']}` : {d['name']} déprécié par son auteur (« {clean(deprecated, 90)} ») "
                                      "→ choisir une alternative maintenue"))
    for product, ver, rel, st in res["runtimes"]:
        if st and st[0]:
            out.append((WARN, "runtime", f"`{rel}` : {RUNTIME_LABEL.get(product, product)} {ver} en fin de vie "
                                         f"({st[1]}) — plus de correctifs de sécurité → passer à {st[2]}"))
    for d, product, st in res["eol"]:
        if st[0]:
            out.append((WARN, "runtime", f"`{d['src']}` : {d['name']} {d['version']} — branche en fin de vie ({st[1]}) "
                                         f"→ passer à {st[2]}"))
    return out


class Code(str):
    """Cellule affichée en `code` (chemin de fichier)."""


class Link(str):
    """Cellule déjà construite (lien OSV dont l'identifiant est validé)."""


def row(*cells):
    def cell(c):
        if not c:
            return "—"
        if isinstance(c, Link):
            return str(c)
        return f"`{clean(c, 160)}`" if isinstance(c, Code) else clean(c, 160)
    return "| " + " | ".join(cell(c) for c in cells) + " |"


def render(res, date, version_str):
    by_id = {id(d): d for d in res["packages"]}
    n_vuln = sum(len(v) for v in res["vulns"].values())
    direct = [d for d in res["packages"] if d["direct"]]
    source = ("vérifié en ligne via OSV.dev (failles et historique), les registres publics (dernière version stable) "
              "et endoflife.date (support)" if res["online"] else
              "**hors ligne** : failles connues et versions stables non vérifiées. Relancer avec `--online` "
              "(accord de l'utilisateur ; seuls des noms et versions de paquets publics sont envoyés)")
    lines = [f"# Dépendances, runtimes et API — {date}", "",
             f"Contrôlé par design-to-dev {version_str} — {source}.", "",
             f"**Bilan : {len(res['packages'])} paquet(s) dont {len(direct)} direct(s), "
             f"{n_vuln if res['online'] else '?'} faille(s) connue(s), {len(res['runtimes'])} runtime(s), "
             f"{len(res['apis'])} API externe(s)**", ""]
    lines += ["## Failles connues", ""]
    if res["vulns"]:
        lines += ["| Paquet | Fichier | Faille | Gravité | Ce qui est touché | Corrigé en | Action |", "|---|---|---|---|---|---|---|"]
        for key, vulns in res["vulns"].items():
            d = by_id[key]
            for v in vulns:
                ref = Link(f"[{clean(v['cves'][0] if v['cves'] else v['id'], 40)}]"
                           f"(https://osv.dev/vulnerability/{urllib.parse.quote(v['id'])})")
                touched = "; ".join(x for x in (v["summary"], v["where"], ", ".join(v["cwe"][:2])) if x)
                action = (f"mettre à jour ≥ {v['fixed']}" if v["fixed"] else
                          "retirer (malveillant)" if v["id"].startswith("MAL-") else "aucun correctif : alternative ou isolement")
                lines.append(row(label(d), Code(d["src"]), ref, v["severity"], touched, v["fixed"], action))
    else:
        lines.append("- aucune faille connue" if res["online"] else "- non vérifié (hors ligne)")
    lines += ["", "## Runtimes et frameworks", ""]
    if res["runtimes"] or res["eol"]:
        lines += ["| Composant | Version | Fichier | Fin de support | Conseil |", "|---|---|---|---|---|"]
        for product, ver, rel, st in res["runtimes"]:
            lines.append(row(RUNTIME_LABEL.get(product, product), ver, Code(rel), st and st[1] or "inconnue",
                             (f"passer à {st[2]}" if st[0] else "maintenu") if st else "vérifier sur le web"))
        for d, product, st in res["eol"]:
            lines.append(row(d["name"], d["version"], Code(d["src"]), st[1], f"passer à {st[2]}" if st[0] else "maintenu"))
    else:
        lines.append("- aucune version de runtime déclarée (engines, .nvmrc, composer.json, go.mod, Dockerfile…)")
    lines += ["", "## Dépendances directes", ""]
    if direct:
        lines += ["| Paquet | Écosystème | Utilisée | Dernière stable | Historique des failles | Fichier |", "|---|---|---|---|---|---|"]
        for d in direct:
            ver, _ = res["latest"].get(id(d), (None, None))
            hist = res["history"].get(id(d))
            behind = ver and d["version"] and vkey(ver)[0] > vkey(d["version"])[0]
            lines.append(row(d["name"], d["eco"], d["version"] or "non figée",
                             (ver + (" (version majeure de retard)" if behind else "")) if ver else
                             ("?" if not res["online"] else "introuvable"),
                             (f"{hist[0]} avis publiés, dernier modifié le {hist[1] or '?'}" if hist[0] else "aucun avis")
                             if hist else "?", Code(d["src"])))
    else:
        lines.append("- aucune dépendance directe déclarée")
    lines += ["", "## À remplacer (déprécié, abandonné, compromis)", ""]
    repl = [f"- [ ] {d['name']} (`{d['src']}`) — {why} → {r}" for d, why, r in res["replace"]]
    replaced = {id(d) for d, _, _ in res["replace"]}
    repl += [f"- [ ] {by_id[k]['name']} (`{by_id[k]['src']}`) — déprécié par son auteur : « {clean(dep, 100)} »"
             for k, (_, dep) in res["latest"].items() if dep and k not in replaced]
    lines += repl or ["- rien"]
    lines += ["", "## À vérifier sur le web (agent)", "",
              "OSV.dev ne couvre pas tout : pour chaque ligne, chercher les avis de sécurité, le changelog et "
              "l'historique des failles, puis noter la conclusion dans `.agents/memory/decisions.md`.", ""]
    web = [f"- {RUNTIME_LABEL.get(p, p)} {v} (`{rel}`) : avis de sécurité de la branche {v}, failles marquantes passées"
           + (f" (ex. {'; '.join(res['notable'][p][:2])})" if res["notable"].get(p) else "")
           for p, v, rel, _ in res["runtimes"]]
    web += [f"- API `{host}` (appelée dans `{rel}`) : incidents de sécurité, version d'API dépréciée, page de statut"
            for host, rel in res["apis"]]
    web += [f"- {d['name']} (`{d['src']}`) : version non figée — figer une version vérifiée"
            for d in res["packages"] if d["direct"] and not d["exact"]][:20]
    lines += web or ["- rien de plus"]
    if res["errors"] or res["net_errors"]:
        lines += ["", "## Non vérifié", ""] + [f"- {e}" for e in res["errors"]] + \
                 [f"- réseau — {e} : needs_validation" for e in res["net_errors"]]
    return "\n".join(lines) + "\n"


def audits_lines(res):
    if not res["packages"] and not res["runtimes"]:
        return []
    if not res["online"]:
        why = "service OSV injoignable" if res["net_errors"] else "hors ligne"
        return [f"needs_validation — {len(res['packages'])} paquet(s) non vérifiés en ligne ({why}) : demander à "
                "l'utilisateur, puis relancer avec `--online` → `docs/security/dependances.md`"]
    n = sum(len(v) for v in res["vulns"].values())
    return [f"OSV.dev : {len(res['packages'])} paquet(s) vérifiés, {n} faille(s) connue(s) → `docs/security/dependances.md`"]
