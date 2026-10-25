# Format de `plan.json`

```json
{
  "source": "C:/Users/me/Downloads/Acme Design System",
  "target": "C:/Users/me/Downloads/acme-design-system",
  "actions": [
    { "src": "tokens/colors.css", "action": "move", "dst": "src/styles/tokens/colors.css",
      "reason": "token de couleur, source de vérité", "confidence": 0.95, "agent": "code" },
    { "src": "readme.md", "action": "move", "dst": "docs/design-system/README.md",
      "reason": "fondations du DS", "confidence": 0.9, "agent": "docs-tooling" },
    { "src": "_ds_manifest.json", "action": "delete",
      "reason": "métadonnées d'export, lu par aucun fichier conservé", "confidence": 0.9, "agent": "docs-tooling" },
    { "src": "assets/logo-copy.png", "action": "delete", "replaced_by": "assets/logo-mark.png",
      "reason": "doublon exact (même hash)", "confidence": 1.0, "agent": "assets" },
    { "src": "uploads/photo-profil.png", "action": "delete", "review": true,
      "reason": "photo de personne non utilisée — à confirmer", "confidence": 0.5, "agent": "assets" },
    { "src": "LICENSE", "action": "keep", "reason": "licence", "confidence": 1.0 }
  ]
}
```

Champs :
- `src` (obligatoire) : chemin relatif à la source, séparateur `/`, exactement comme dans `inventory.json`.
- `action` (obligatoire) : `keep` | `move` | `delete`.
- `dst` : obligatoire pour `move` ; relatif à la cible.
- `reason` (obligatoire), `confidence` (0–1), `agent`, `review` (bool), `replaced_by` (chemin source du remplaçant).

Un dossier entier peut être traité avec un glob dans `src` (`"uploads/pasted-*"`, `"node_modules/**"`) et une action `delete`, ou `move` avec `dst` finissant par `/` (le reste du chemin est conservé : `"src": "ui_kits/**", "dst": "prototypes/"` → `ui_kits/admin/index.html` devient `prototypes/admin/index.html`). Une entrée explicite l'emporte sur un glob ; entre deux globs, le plus long l'emporte.

Avant `apply`, les éléments `review: true` doivent avoir été tranchés par l'utilisateur (retirer `review` ou changer l'action). `apply --apply` refuse un plan qui contient encore des `review`.
