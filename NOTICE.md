# Droits d'auteur et mentions

## design-to-dev

Copyright © 2026 duckysface.

Le code, la documentation et les modèles de ce dépôt sont publiés sous [licence MIT](LICENSE) : tu peux les utiliser, les copier, les modifier et les redistribuer, y compris à des fins commerciales, à condition de conserver l'avis de copyright et le texte de la licence. Le logiciel est fourni **« tel quel », sans garantie**.

## Ton travail t'appartient

design-to-dev ne revendique **aucun droit** sur :

- tes fichiers de design, d'origine ou réorganisés ;
- les fichiers générés dans ton projet (README, ADR, `docs/`, mémoire `.agents/`, rapports).

Ils t'appartiennent et tu peux leur appliquer la licence de ton choix. La skill n'ajoute jamais de licence à ton projet sans te le demander.

Les modèles copiés dans ton projet (`AGENTS.md`, `PROTOCOLE.md`, `GRAPHE.md`, `memory_hook.py`) restent sous licence MIT, mais tu peux les modifier librement et tu n'as pas à citer design-to-dev dans ton produit.

## Travaux de tiers

design-to-dev **n'inclut aucun code de tiers**. Les projets ci-dessous sont cités ou s'installent séparément, avec ton accord, sous leur propre licence. [`references/security-kit.json`](references/security-kit.json) ne contient que des chemins, des commits et des empreintes ; `security-kit install` télécharge les fichiers depuis GitHub et les copie dans **ton** projet avec leur licence (`LICENSE` dans chaque dossier, `THIRD_PARTY_NOTICES.md`) :

| Projet | Lien avec design-to-dev |
|---|---|
| [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) | Méthode d'audit résumée dans [`references/security.md`](references/security.md) ; installable en option et dans le kit de sécurité (MIT, © Cloudflare, Inc.) |
| [UnitOneAI/SecuritySkills](https://github.com/UnitOneAI/SecuritySkills) | Inspiration des checklists de sécurité ; skills du kit de sécurité (MIT, © UnitOne.ai) |
| [trailofbits/skills](https://github.com/trailofbits/skills) | Skills du kit de sécurité (CC BY-SA 4.0, © Trail of Bits) : copiées sans modification ; toute adaptation doit rester sous CC BY-SA 4.0 avec attribution |
| [obra/superpowers](https://github.com/obra/superpowers) | Skill de planification, installable en option |

## Référentiels

- **OWASP ASVS 4.0.3** — © OWASP Foundation, sous licence CC BY-SA 4.0. design-to-dev cite seulement les identifiants des exigences (ex. `V2.4.1`).
- **CWE™** — marque de The MITRE Corporation. Seuls les identifiants sont cités (ex. `CWE-79`).
- **CVE®** — marque de The MITRE Corporation. Les identifiants listés dans [`references/vulnerable-libs.json`](references/vulnerable-libs.json) proviennent des avis publics.

## Sources de données consultées en ligne

Avec `--online` seulement : [OSV.dev](https://osv.dev) (données d'avis sous licences de leurs sources, majoritairement CC-BY 4.0), [endoflife.date](https://endoflife.date) (MIT) et les API publiques des registres de paquets. Rien de ces sources n'est inclus dans design-to-dev ; les rapports citent les identifiants et les liens.

## Marques

Claude, Claude Code et Claude Design sont des marques d'Anthropic. Codex est une marque d'OpenAI. Figma, v0, Lovable, Bolt, Cursor, Gemini, GitHub Copilot, Supabase, Cloudflare et les frameworks cités appartiennent à leurs propriétaires respectifs. design-to-dev est un projet indépendant, **sans lien ni approbation** de ces sociétés ; leurs noms servent seulement à indiquer la compatibilité.
