# Stacks par intention

Source de vérité des choix techniques. `scripts/detect_project.py scan` propose une intention ; l'utilisateur confirme. Si le design utilise déjà un framework compatible (ex. maquettes React alors que la stack conseillée est SvelteKit), **demander** : garder le framework existant (réutilisation maximale) ou porter vers la stack conseillée. Par défaut : garder l'existant s'il est sain.

Résumé :

| Intention | Stack conseillée |
|---|---|
| Site vitrine | Astro + Tailwind + Motion (îlots Svelte/React), Rust Axum si dynamique |
| Dashboard | SvelteKit (ou Next.js) + Rust Axum + PostgreSQL |
| Desktop | Tauri 2 |
| iOS / macOS | SwiftUI (+ cœur Rust via UniFFI) |
| Android | Jetpack Compose (+ cœur Rust via UniFFI) |
| Backend | Rust Axum + SQLx + PostgreSQL |

---

## Site vitrine

- **Frontend** : Astro (HTML statique, zéro JS par défaut), îlots Svelte ou React seulement pour l'interactif.
- **Animations** : Motion (ex-Framer Motion), GSAP (ScrollTrigger), View Transitions API. Respecter `prefers-reduced-motion`.
- **Style** : Tailwind CSS ; les tokens du design system deviennent `@theme` / `tailwind.config`.
- **Dynamique** (formulaire de contact, newsletter, blog) : endpoint Rust Axum, ou Astro SSR minimal.
- **Sécurité** : CSP stricte (pas de `unsafe-inline`, nonces/hashes), HTTPS forcé + HSTS, cookies `SameSite`, validation serveur de tout formulaire, jamais de HTML non échappé (`set:html` interdit sur du contenu utilisateur), anti-spam (rate limit + honeypot).

```
site/
  src/pages/          # une page Astro par écran du design
  src/components/     # composants .astro + îlots .svelte/.tsx
  src/layouts/
  src/styles/         # tokens.css, global.css
  public/             # favicon, robots.txt, images optimisées
  api/                # (optionnel) Rust Axum pour formulaires
```

## Dashboard (connexion admin + utilisateur)

- **Frontend** : SvelteKit ou Next.js ; TanStack Query (cache, invalidation) ; shadcn/ui (ou shadcn-svelte) + Tailwind ; graphiques Recharts (React) ou ECharts.
- **Backend** : Rust Axum + Tower (ou Actix-web), SQLx + PostgreSQL (migrations versionnées).
- **Auth** : hash Argon2id ; sessions par cookie `HttpOnly; Secure; SameSite=Strict` ; MFA TOTP ; rôles admin/utilisateur vérifiés **côté serveur** sur chaque route (jamais seulement en masquant l'UI).
- **Protection** : rate limiting (tower-governor), verrouillage progressif du compte, jeton CSRF sur toute requête d'écriture, en-têtes de sécurité (CSP, HSTS, X-Content-Type-Options, frame-ancestors), journal d'audit (connexions, actions admin).
- **Alternative managée** : Supabase (Auth + Postgres + Row Level Security activé sur **toutes** les tables exposées).

```
web/                  # SvelteKit : src/routes/(auth)/login, (app)/..., (admin)/...
  src/lib/components/ # composants issus du design
  src/lib/api/        # client typé + TanStack Query
api/                  # Rust Axum
  src/routes/ src/auth/ src/db/ src/middleware/
  migrations/
```

## Desktop

- **Tauri 2** : backend Rust, UI Svelte/React/Vue (réutiliser les écrans du design tels quels). Electron seulement si une dépendance Node l'impose (plus lourd, surface d'attaque plus grande).
- **Stockage** : SQLite via rusqlite ou sqlx ; secrets dans le trousseau OS (crate `keyring`), jamais en clair dans un fichier.
- **Sécurité** : capabilities/permissions IPC minimales (allowlist par commande), CSP activée (`csp` non nul dans `tauri.conf.json`), pas de Node dans le renderer, plugin updater avec signature, signature de code obligatoire (Windows + macOS notarisation).

```
app/
  src/                # UI (écrans du design)
  src-tauri/src/      # commandes Rust (#[tauri::command])
  src-tauri/capabilities/
  src-tauri/tauri.conf.json
```

## iOS / macOS

- **Swift + SwiftUI** ; animations natives (`matchedGeometryEffect`, `withAnimation`, `PhaseAnimator`).
- **Stockage** : SwiftData (ou Core Data) ; secrets dans le Keychain.
- **Logique partagée** : cœur Rust exposé via UniFFI (même logique que le backend/desktop).
- **Alternatives** : Tauri 2 mobile, Flutter.
- **Sécurité** : App Transport Security (pas de `NSAllowsArbitraryLoads`), LocalAuthentication (Face ID / Touch ID), certificate pinning pour l'API.

## Android

- **Kotlin + Jetpack Compose** ; cœur Rust via UniFFI.
- **Stockage** : Room, DataStore ; secrets dans Android Keystore ; BiometricPrompt.
- **Alternatives** : Tauri 2 mobile, Flutter.
- **Sécurité** : R8/ProGuard, Network Security Config, certificate pinning, `usesCleartextTraffic="false"`, `debuggable` et `allowBackup` désactivés en release.

Mobile (iOS + Android) avec cœur Rust :
```
core/                 # crate Rust + UniFFI (.udl ou proc-macros)
ios/                  # projet Xcode SwiftUI
android/              # projet Gradle Compose
```

## Backend commun

- **Rust Axum** (ou Actix-web), PostgreSQL + SQLx, Redis/Valkey (sessions, rate limit, cache).
- **Auth** : JWT court (15 min) + refresh token en cookie `HttpOnly` (rotation à chaque usage), ou sessions serveur ; Argon2id.
- **Protection** : rate limiting par IP **et** par compte, validation des entrées (crate `validator`), CSRF, en-têtes de sécurité, secrets en variables d'environnement (`.env.example` sans valeurs), journalisation des accès sensibles (sans données personnelles ni secrets).

## Menaces → protections

| Menace | Protection |
|---|---|
| Injection SQL | Requêtes paramétrées SQLx (`query!` / `bind`), jamais de `format!` |
| XSS | Échappement automatique du framework + CSP stricte |
| CSRF | Cookies `SameSite` + jetons CSRF |
| Brute force | Rate limiting, verrouillage progressif, MFA |
| Vol de session | Cookies `HttpOnly` + `Secure`, rotation de session au login |
| Fuite de données | TLS partout, chiffrement au repos, secrets hors du code |
| Dépendances vulnérables | `cargo audit`, `npm audit`, Dependabot |
