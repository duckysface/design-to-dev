#!/usr/bin/env python3
"""design-to-dev : base de sécurité statique et exigences par stack.

Lecture seule : rien n'est exécuté. Chaque résultat est un CANDIDAT (motif repéré) ou
NEEDS_VALIDATION (contrôle invisible dans le code : à vérifier au déploiement). Aucune
sévérité n'est attribuée ici : seule une vérification humaine ou un audit complet
(skill security-audit) confirme une vulnérabilité.

  security_check.py scan <dossier> [--json] [--out findings.json]
  security_check.py foundations <cible> [--out docs/security/fondations.md] [--strict] [--run-audits] [--online] [--json]
  security_check.py deps <cible> [--online] [--out docs/security/dependances.md] [--strict] [--json]
  security_check.py requirements --intent dashboard[,backend] [--inventory design-inventory.json] [--out exigences.md]
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

SKIP_DIRS = {"node_modules", ".git", ".next", ".nuxt", ".svelte-kit", ".turbo", ".cache", "dist", "build", "out",
             "target", "coverage", "__pycache__", ".venv", "venv", "vendor", "Pods", "DerivedData", ".gradle"}
CODE_EXT = {".html", ".htm", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".astro", ".rs",
            ".py", ".swift", ".kt", ".dart", ".json", ".toml", ".yaml", ".yml", ".xml", ".plist", ".env", ".sql"}
MAX_READ = 1024 * 1024
WEB = ("vitrine", "dashboard", "backend")

# (id, titre, regex, extensions ou None, CWE, ASVS, correctif minimal)
RULES = [
    ("xss-sink", "Insertion de HTML brut (sink XSS)",
     r"\.innerHTML\s*=|\.outerHTML\s*=|dangerouslySetInnerHTML|v-html=|\{@html\s|set:html=|document\.write\(|insertAdjacentHTML\(",
     None, "CWE-79", "V5.3.3", "Rendre en texte (textContent / interpolation échappée) ou assainir avec DOMPurify."),
    ("eval", "Exécution de code dynamique",
     r"\beval\s*\(|new\s+Function\s*\(|setTimeout\s*\(\s*[\"'`]", None, "CWE-95", "V5.2.4",
     "Supprimer eval/new Function ; parser les données (JSON.parse) au lieu de les exécuter."),
    ("sql-concat", "Requête SQL construite par concaténation",
     r"""(?i)(format!\s*\(\s*"[^"]*\b(select|insert|update|delete)\b|["'`]\s*(select|insert|update|delete)\b[^"'`]*["'`]\s*\+|`[^`]*\b(select|insert|update|delete)\b[^`]*\$\{)""",
     None, "CWE-89", "V5.3.4", "Requête paramétrée (sqlx::query!(..., $1) / .bind(), placeholders)."),
    ("cleartext-http", "URL en http:// (trafic en clair)",
     r"""["'`(]http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]|www\.w3\.org|schemas\.|ns\.adobe|purl\.org|xmlns)""",
     {".html", ".htm", ".js", ".mjs", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".astro", ".rs", ".swift", ".kt", ".dart"},
     "CWE-319", "V9.1.1", "Passer en https:// ; HSTS côté serveur."),
    ("token-localstorage", "Jeton d'authentification dans localStorage/sessionStorage",
     r"(?i)(local|session)Storage\.setItem\(\s*[\"'`][^\"'`]*(token|jwt|auth|session)", None, "CWE-922", "V3.2.3",
     "Garder la session dans un cookie HttpOnly; Secure; SameSite=Strict posé par le serveur."),
    ("js-cookie", "Cookie manipulé en JavaScript (pas HttpOnly)",
     r"document\.cookie\s*=", None, "CWE-1004", "V3.4.2", "Poser les cookies de session côté serveur avec HttpOnly."),
    ("weak-hash", "Hash faible pour un mot de passe",
     r"(?i)(md5|sha1|sha256)\s*\(.{0,40}pass|pass\w*.{0,40}(md5|sha1)\b", None, "CWE-916", "V2.4.1",
     "Argon2id (crate argon2 / bibliothèque équivalente) avec sel aléatoire."),
    ("weak-random", "Math.random pour un secret",
     r"Math\.random\(\).{0,60}\b(?:(?i:token|secret|password|passwd|otp|nonce|salt|session)\w*|(?i:id|uuid|code)"
     r"|\w+(?:Id|ID|_id|Token|Secret))\b|(?i:\w*(?:token|secret|otp|nonce))\s*=.{0,30}Math\.random",
     None, "CWE-338", "V6.3.1", "crypto.getRandomValues / crypto.randomUUID / rand::rngs::OsRng."),
    ("cors-wildcard", "CORS ouvert à toutes les origines",
     r"""(?i)Access-Control-Allow-Origin["']?\s*[:,]\s*["']\*|CorsLayer::(permissive|very_permissive)|allow_origin\(\s*Any|origin:\s*["']\*["']|cors\(\s*\)""",
     None, "CWE-942", "V14.5.3", "Lister explicitement les origines autorisées."),
    ("jwt-long", "JWT à durée de vie longue",
     r"""(?i)expiresIn\s*[:=]\s*["']?(\d+\s*d|[3-9]\d*\s*h|\d{2,}\s*h|\d{6,})|exp.{0,20}days\(\s*\d""", None, "CWE-613", "V3.3.1",
     "Access token ≤ 15 min + refresh token en cookie HttpOnly avec rotation."),
    ("tauri-csp-null", "CSP désactivée dans Tauri", r'"csp"\s*:\s*null', {".json"}, "CWE-1021", "V14.4.3",
     "Définir app.security.csp (default-src 'self')."),
    ("tauri-global", "API Tauri exposée globalement", r'"withGlobalTauri"\s*:\s*true', {".json"}, "CWE-749", "V1.14.6",
     "withGlobalTauri: false ; importer @tauri-apps/api dans le bundle."),
    ("tauri-wide-perm", "Permission Tauri large (shell / fs global)",
     r'"(shell:allow-execute|shell:default|fs:default|fs:allow-.*-recursive|fs:scope-home|http:default)"', {".json"},
     "CWE-250", "V1.14.6", "Restreindre les capabilities aux commandes et chemins nécessaires."),
    ("electron-node", "Electron : Node ou isolation désactivée dans le renderer",
     r"nodeIntegration\s*:\s*true|contextIsolation\s*:\s*false|webSecurity\s*:\s*false|sandbox\s*:\s*false", None,
     "CWE-94", "V14.2.1", "nodeIntegration:false, contextIsolation:true, sandbox:true, preload minimal."),
    ("android-cleartext", "Android : trafic en clair autorisé", r'usesCleartextTraffic\s*=\s*"true"|cleartextTrafficPermitted="true"',
     {".xml"}, "CWE-319", "V9.1.1", "usesCleartextTraffic=\"false\" + Network Security Config."),
    ("android-debug", "Android : debuggable ou backup activés", r'android:(debuggable|allowBackup)\s*=\s*"true"', {".xml"},
     "CWE-489", "V14.1.1", "Désactiver en release."),
    ("ios-ats", "iOS : App Transport Security désactivé", r"NSAllowsArbitraryLoads</key>\s*<true", {".plist"},
     "CWE-319", "V9.1.1", "Retirer NSAllowsArbitraryLoads ; exceptions par domaine seulement."),
    ("supabase-service-key", "Clé service_role Supabase côté client",
     r"(?i)service_role|SUPABASE_SERVICE_ROLE", {".html", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".astro"},
     "CWE-798", "V2.10.4", "Ne jamais exposer service_role au navigateur ; anon key + RLS."),
]
RULES = [(i, t, re.compile(r), e, c, a, f) for i, t, r, e, c, a, f in RULES]

SECRET_RE = re.compile(
    r"""(?i)(?P<k>api[_-]?key|secret|passw(or)?d|pwd|token|private[_-]?key|client[_-]?secret|database_url|dsn)\s*["']?\s*[:=]\s*["'](?P<v>[^"'\s$<{]{8,})["']"""
    r"""|(?P<v2>sk_live_[0-9A-Za-z]{10,}|sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|xox[bp]-[0-9A-Za-z-]{10,}|-----BEGIN (RSA |EC )?PRIVATE KEY-----)""")
PLACEHOLDER_RE = re.compile(r"(?i)(example|changeme|your[_-]|xxx|placeholder|dummy|test|<|\*{3}|process\.env|import\.meta\.env|env\()")


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            yield Path(dirpath) / name


def read(path):
    try:
        with open(path, "rb") as f:
            return f.read(MAX_READ).decode("utf-8", errors="replace")
    except OSError:
        return ""


def mask(value):
    return value[:4] + "…" + f"({len(value)} car.)"


def finding(rule, title, rel, line, cwe, asvs, fix, status="candidate", evidence=""):
    return {"rule": rule, "title": title, "path": rel, "line": line, "status": status, "cwe": cwe, "asvs": asvs,
            "fix": fix, "evidence": evidence[:160]}


def scan_file(rel, text, ext):
    out = []
    lines = text.splitlines()
    for rid, title, rx, exts, cwe, asvs, fix in RULES:
        if exts and ext not in exts:
            continue
        for n, line in enumerate(lines, 1):
            if len(line) > 2000:
                continue
            if rx.search(line):
                out.append(finding(rid, title, rel, n, cwe, asvs, fix, evidence=line.strip()))
    for n, line in enumerate(lines, 1):
        for m in SECRET_RE.finditer(line):
            value = m.group("v") or m.group("v2")
            if not value or PLACEHOLDER_RE.search(value):
                continue
            out.append(finding("hardcoded-secret", "Secret probable dans le code", rel, n, "CWE-798", "V2.10.4",
                               "Déplacer dans une variable d'environnement ; révoquer et régénérer la valeur exposée.",
                               evidence=f"{m.group('k') or 'clé'} = {mask(value)}"))
    return out


def collect(root):
    """Liste des constats (candidate / needs_validation) sans rien afficher."""
    root = Path(root).resolve()
    findings, names, has_csp, has_html = [], set(), False, False
    for p in walk(root):
        rel = p.relative_to(root).as_posix()
        names.add(p.name.lower())
        ext = p.suffix.lower() if p.suffix else (".env" if p.name.startswith(".env") else "")
        if p.name.startswith(".env") and p.name not in (".env.example", ".env.sample", ".env.template"):
            findings.append(finding("env-file", "Fichier .env réel présent", rel, 0, "CWE-538", "V14.3.3",
                                    "Ne jamais committer .env : l'ajouter au .gitignore, fournir .env.example sans valeurs."))
        if ext not in CODE_EXT:
            continue
        text = read(p)
        if ext in (".html", ".htm") and re.search(r"<(html|body)\b", text, re.I):
            has_html = True
        if re.search(r"Content-Security-Policy|\"csp\"\s*:|contentSecurityPolicy|csp\s*:\s*\{", text):
            has_csp = True
        findings += scan_file(rel, text, ext)
    if "package.json" in names and not names & {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "bun.lock"}:
        findings.append(finding("no-lockfile", "package.json sans lockfile", "package.json", 0, "CWE-1104", "V14.2.4",
                                "Committer le lockfile ; npm ci en CI ; npm audit / Dependabot."))
    if "cargo.toml" in names and "cargo.lock" not in names:
        findings.append(finding("no-lockfile", "Cargo.toml sans Cargo.lock", "Cargo.toml", 0, "CWE-1104", "V14.2.4",
                                "Committer Cargo.lock pour un binaire ; cargo audit en CI."))
    if has_html and not has_csp:
        findings.append(finding("csp-unknown", "Aucune CSP visible dans le code", ".", 0, "CWE-1021", "V14.4.3",
                                "Définir une CSP stricte (en-tête serveur ou meta) ; vérifier sur le déploiement réel.",
                                status="needs_validation"))
    findings.append(finding("deploy-headers", "HTTPS, HSTS et en-têtes de sécurité non vérifiables depuis le code", ".", 0,
                            "CWE-693", "V14.4", "Contrôler sur l'environnement déployé (curl -I) : HSTS, CSP, "
                            "X-Content-Type-Options, frame-ancestors, Referrer-Policy.", status="needs_validation"))
    return findings


def scan(root, as_json, out_path):
    root = Path(root).resolve()
    if not root.is_dir():
        sys.exit(f"Dossier introuvable : {root}")
    findings = collect(root)
    report = {"root": str(root), "findings": findings,
              "note": "candidate = motif à vérifier ; needs_validation = dépend du déploiement. Aucune sévérité ici."}
    if out_path:
        Path(out_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    cand = [f for f in findings if f["status"] == "candidate"]
    print(f"{len(cand)} candidat(s), {len(findings) - len(cand)} à valider au déploiement — {root}")
    by_rule = {}
    for f in findings:
        by_rule.setdefault((f["rule"], f["title"], f["cwe"], f["status"]), []).append(f)
    for (rid, title, cwe, status), items in sorted(by_rule.items(), key=lambda kv: kv[0][3]):
        print(f"\n[{status}] {title} ({cwe}) — {len(items)}")
        for f in items[:8]:
            loc = f"{f['path']}:{f['line']}" if f["line"] else f["path"]
            print(f"  - {loc}  {f['evidence']}")
        if len(items) > 8:
            print(f"  … +{len(items) - 8}")
        print(f"  → {items[0]['fix']}")
    if out_path:
        print(f"\n→ {out_path}")
    return 0


# --------------------------------------------------------------------------- exigences

BASE = {
    "vitrine": [
        "CSP stricte sans `unsafe-inline` (nonces/hashes), `frame-ancestors 'none'` — ASVS V14.4.3",
        "HTTPS forcé + HSTS (`max-age=31536000; includeSubDomains`) — ASVS V9.1.1",
        "Aucun HTML non échappé (`set:html` / `innerHTML` interdits sur du contenu externe) — ASVS V5.3.3",
        "Formulaires : validation serveur, rate limit + honeypot anti-spam, cookies `SameSite` — ASVS V5.1.1, V11.1.4",
        "Images et polices servies depuis le même domaine ou CDN listé dans la CSP — ASVS V14.4.3",
    ],
    "dashboard": [
        "Mots de passe hachés en Argon2id (jamais MD5/SHA) — ASVS V2.4.1",
        "Session en cookie `HttpOnly; Secure; SameSite=Strict`, rotation de l'identifiant au login — ASVS V3.2.1, V3.4.1–3",
        "MFA TOTP (obligatoire pour les admins) — ASVS V2.8",
        "Rôles admin/utilisateur vérifiés côté serveur sur chaque route et chaque requête (contrôle d'accès objet par objet) — ASVS V4.1.1, V4.2.1",
        "Rate limiting (tower-governor) + verrouillage progressif du compte — ASVS V2.2.1",
        "Jeton CSRF sur toute requête d'écriture — ASVS V4.2.2",
        "En-têtes de sécurité (CSP, HSTS, X-Content-Type-Options, Referrer-Policy) — ASVS V14.4",
        "Journal d'audit : connexions, échecs, actions admin (sans mot de passe ni donnée personnelle) — ASVS V7.1.1, V7.2.1",
        "Supabase si choisi : RLS activé sur toutes les tables exposées, clé service_role jamais côté client — ASVS V4.1.1",
    ],
    "backend": [
        "Requêtes SQLx paramétrées uniquement (`query!` / `bind`) — ASVS V5.3.4",
        "Validation de chaque entrée (crate `validator`), taille max des corps de requête — ASVS V5.1.1",
        "JWT ≤ 15 min + refresh token en cookie HttpOnly avec rotation, ou sessions serveur — ASVS V3.5",
        "Rate limiting par IP et par compte — ASVS V2.2.1",
        "CORS : liste explicite d'origines — ASVS V14.5.3",
        "Secrets en variables d'environnement, `.env.example` sans valeurs — ASVS V2.10.4",
        "Erreurs génériques côté client, détails seulement dans les logs serveur — ASVS V7.4.1",
        "`cargo audit` + `npm audit` + Dependabot en CI — ASVS V14.2.1",
    ],
    "desktop": [
        "Tauri 2 : capabilities minimales (allowlist par commande et par chemin) — ASVS V1.4",
        "CSP définie dans `tauri.conf.json`, `withGlobalTauri: false` — ASVS V14.4.3",
        "Aucun Node dans le renderer ; valider les arguments de chaque `#[tauri::command]` — ASVS V5.1.1",
        "Secrets dans le trousseau OS (crate `keyring`), SQLite local sans secret en clair — ASVS V2.10.4",
        "Updater signé + signature de code (Windows) et notarisation (macOS) — ASVS V10.3.2",
    ],
    "ios": [
        "App Transport Security actif (pas de `NSAllowsArbitraryLoads`) — ASVS V9.1.1",
        "Secrets et jetons dans le Keychain — ASVS V2.10.4",
        "LocalAuthentication (Face ID / Touch ID) pour les actions sensibles — ASVS V2.8",
        "Certificate pinning vers l'API — ASVS V9.2.1",
    ],
    "android": [
        "`usesCleartextTraffic=\"false\"` + Network Security Config + certificate pinning — ASVS V9.1.1",
        "Secrets dans Android Keystore, BiometricPrompt pour les actions sensibles — ASVS V2.10.4",
        "R8/ProGuard ; `debuggable` et `allowBackup` à false en release — ASVS V14.1.3",
    ],
}
FROM_DESIGN = {
    "auth": "Écran de connexion détecté → anti brute-force, message d'erreur identique pour email inconnu / mauvais mot de passe",
    "signup": "Inscription détectée → vérification d'email, politique de mot de passe (ASVS V2.1), anti-bot",
    "mfa": "Écran MFA détecté → codes TOTP à usage unique, codes de récupération hachés",
    "uploads": "Upload détecté → type MIME vérifié côté serveur, taille max, stockage hors webroot, nom de fichier régénéré",
    "payments": "Paiement détecté → jamais de numéro de carte sur nos serveurs (Stripe Elements / Checkout), webhooks signés",
}


def requirements(intents, inventory, out_path):
    intents = [i.strip() for i in intents.split(",") if i.strip()]
    unknown = [i for i in intents if i not in BASE]
    if unknown:
        sys.exit(f"Intention inconnue : {', '.join(unknown)} (choix : {', '.join(BASE)})")
    if any(i in ("dashboard", "vitrine") for i in intents) and "backend" not in intents:
        intents.append("backend")
    contract = {}
    if inventory:
        contract = json.loads(Path(inventory).read_text(encoding="utf-8")).get("backend_contract", {})
    lines = ["# Exigences de sécurité", "",
             f"Intentions : {', '.join(intents)}. Source : `references/stacks.md` + écrans du design.", ""]
    for i in intents:
        lines += [f"## {i}", ""] + [f"- [ ] {r}" for r in BASE[i]] + [""]
    derived = [FROM_DESIGN[k] for k in FROM_DESIGN if contract.get(k)]
    if contract.get("roles"):
        derived.append(f"Rôles {', '.join(contract['roles'])} → matrice d'autorisations par endpoint, testée")
    if derived:
        lines += ["## Exigences issues du design", ""] + [f"- [ ] {d}" for d in derived] + [""]
    if contract.get("endpoints"):
        lines += ["## Endpoints à protéger", "", "| Endpoint | Auth | Rôle | Validation | Rate limit |", "|---|---|---|---|---|"]
        for e in contract["endpoints"]:
            public = "/auth/login" in e or "/auth/register" in e
            lines.append(f"| `{e}` | {'non' if public else 'oui'} | {'public' if public else 'à définir'} | oui | "
                         f"{'strict' if public else 'standard'} |")
        lines.append("")
    lines += ["## Contrôle", "", "- [ ] `python $SKILL/scripts/security_check.py scan <projet>` sans candidat ouvert",
              "- [ ] Audit `security-audit` (Cloudflare) en mode guidance avant la mise en production",
              "- [ ] En-têtes vérifiés sur l'environnement déployé", ""]
    text = "\n".join(lines)
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(text, encoding="utf-8")
        print(f"→ {out_path}")
    else:
        print(text)
    return 0


def load_foundations():
    import importlib.util
    spec = importlib.util.spec_from_file_location("d2d_foundations", Path(__file__).with_name("foundations.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def skill_version():
    skill = Path(__file__).resolve().parent.parent
    for f in (skill / ".version", skill / "package.json"):
        if f.is_file():
            text = f.read_text(encoding="utf-8")
            return "v" + (json.loads(text).get("version", "?") if f.suffix == ".json" else text.strip())
    return "v?"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("scan")
    a.add_argument("folder")
    a.add_argument("--json", action="store_true")
    a.add_argument("--out")
    f = sub.add_parser("foundations", help="contrôle des fondations → docs/security/fondations.md")
    f.add_argument("folder")
    f.add_argument("--out")
    f.add_argument("--strict", action="store_true", help="code 1 s'il reste un ❌")
    f.add_argument("--run-audits", action="store_true", help="lancer npm/cargo audit, osv-scanner (accord utilisateur)")
    f.add_argument("--online", action="store_true",
                   help="vérifier failles, versions stables et support en ligne (OSV.dev, registres, endoflife.date)")
    f.add_argument("--json", action="store_true")
    d = sub.add_parser("deps", help="failles connues, versions stables et support des dépendances → dependances.md")
    d.add_argument("folder")
    d.add_argument("--out")
    d.add_argument("--online", action="store_true", help="envoie seulement des noms et versions de paquets publics")
    d.add_argument("--strict", action="store_true", help="code 1 s'il reste un ❌")
    d.add_argument("--json", action="store_true")
    b = sub.add_parser("requirements")
    b.add_argument("--intent", required=True)
    b.add_argument("--inventory")
    b.add_argument("--out")
    args = ap.parse_args()
    if args.cmd == "scan":
        return scan(args.folder, args.json, args.out)
    if args.cmd == "foundations":
        return load_foundations().run(args.folder, args.out, args.strict, args.run_audits, args.json, collect,
                                      skill_version(), args.online)
    if args.cmd == "deps":
        return load_foundations().run_deps(args.folder, args.out, args.online, args.json, args.strict, skill_version())
    return requirements(args.intent, args.inventory, args.out)


if __name__ == "__main__":
    sys.exit(main())
