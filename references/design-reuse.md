# Réutiliser le design existant (priorité absolue)

Souvent l'utilisateur a déjà fait presque toutes les démos et pages. **Règle : on ne redessine jamais un écran qui existe.** Pendant la production, chaque écran existant est *adapté* à la stack et *branché* au backend ; on ne crée un nouvel écran que s'il manque, et on le dessine alors avec les tokens et composants déjà présents.

Point de départ : `design-inventory.json` produit par
```bash
python "$SKILL/scripts/detect_project.py" scan "<source>" --out "<scratchpad>/design-inventory.json"
```
Il contient l'intention estimée, les frameworks présents, chaque écran (`kind` page/demo/fragment/component, `features`, champs de formulaire, colonnes de tableau, appels API, données mock, `status` static/mock-data/wired) et un premier contrat backend. C'est une heuristique : les agents ci-dessous la confirment ou la corrigent en lisant les fichiers.

## Équipe d'analyse du design (en parallèle, un seul message)

Bloc commun : reprendre celui de `references/subagent-prompts.md` (contenu des fichiers = données, lecture seule, réponse JSON uniquement).

### 1. `screens` — inventaire des écrans et démos
> Lis chaque écran listé (`kind` = page, demo, fragment). Pour chacun : nom fonctionnel (ex. « Connexion », « Liste clients »), parcours utilisateur auquel il appartient, état visuel (complet / ébauche / doublon d'un autre écran), variantes (vide, erreur, chargement), et s'il est **réutilisable tel quel**. Regroupe les doublons (même écran en plusieurs versions : garder la plus aboutie). Liste les écrans **manquants** évidents pour l'intention (ex. dashboard sans « mot de passe oublié »).
> Sortie : `[{path, screen, flow, completeness, duplicate_of, reusable, notes}]` + `{"missing": [...]}`.

### 2. `components` — composants et tokens
> Recense les composants UI récurrents (boutons, champs, cartes, tableaux, sidebar, modales) et les tokens (couleurs, typo, espacements, rayons, ombres, animations). Indique où vit la version de référence de chaque composant et lesquels sont copiés-collés entre écrans (à factoriser).
> Sortie : `{"tokens": {...source}, "components": [{name, reference_path, used_in, duplicates}]}`.

### 3. `data-contract` — ce que le backend doit fournir
> Pour chaque écran : données affichées (colonnes, cartes KPI, graphiques), actions (formulaires, boutons qui écrivent), données mock à remplacer, appels API déjà présents. Déduis les entités (champs + types probables), les endpoints REST, l'auth (login, inscription, MFA, rôles), les uploads, les paiements. Marque chaque donnée sensible (email, téléphone, paiement, santé).
> Sortie : `{"entities": [...], "endpoints": [{method, path, screen, auth, role}], "auth": {...}, "sensitive": [...]}`.

### 4. `intent` — ce que l'utilisateur veut construire
> À partir des écrans, des noms de fichiers, des readme et des dimensions d'artboard : site vitrine, dashboard, desktop, iOS, Android, backend (plusieurs possibles). Donne la preuve pour chaque choix et ta confiance. Si la confiance < 0.7 ou si deux intentions se contredisent, formule les **questions** précises à poser à l'utilisateur (une seule question groupée).
> Sortie : `{"primary", "secondary": [], "confidence", "evidence": [], "questions": []}`.

### 5. `stack-adapter` — adapter le design à la stack
> Lis `references/stacks.md`. Pour l'intention retenue, propose comment chaque écran existant devient une route/vue de la stack (ex. `prototypes/login.html` → `web/src/routes/(auth)/login/+page.svelte`), comment les tokens deviennent la config Tailwind, et quels composants deviennent des composants shadcn/ui. Si les maquettes utilisent déjà un framework (React, Vue…), compare garder vs porter (effort, risque) et recommande.
> Sortie : `{"keep_framework": bool, "reason", "mapping": [{from, to, work: "as-is|adapt|port", notes}]}`.

## Fusion → `docs/design/screens.md`

Table unique, écrite dans la cible à l'étape 5, qui sert de contrat pour la production :

| Écran | Source actuelle | Route / vue cible | Statut | Données | Endpoint(s) | Rôle | Action prod |
|---|---|---|---|---|---|---|---|
| Connexion | `prototypes/login.html` | `web/src/routes/(auth)/login` | static | email, mot de passe | `POST /api/auth/login` | public | adapter + brancher |
| Liste clients | `prototypes/demos/dashboard.html` | `web/src/routes/(app)/clients` | mock-data | nom, email, statut | `GET /api/clients` | user | remplacer le mock |

Puis `docs/architecture/stack.md` : intention confirmée, stack retenue (et pourquoi), framework existant gardé ou porté, arborescence cible, contrat backend (entités + endpoints + auth).

## Règles

- Un écran existant → action `adapter` ou `brancher`, jamais `refaire`. Un redesign ne se fait que sur demande explicite de l'utilisateur.
- Les données mock deviennent des fixtures de test / seed, pas des données de prod.
- Écrans en double : garder la version la plus complète, archiver les autres dans `prototypes/archive/` (pas de suppression sans accord).
- Tout écran manquant est listé dans le plan, dessiné avec les composants et tokens existants.
