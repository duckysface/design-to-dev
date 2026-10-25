# Mémoire graphe du projet (OBLIGATOIRE)

Ce projet tient un graphe de connaissances dans `.claude/graph/graph.json`. Il complète le dossier `.claude/memory/` (journal, état, décisions) : la mémoire texte dit *pourquoi* et *où on en est*, le graphe dit *qui dépend de quoi*.

Les hooks enregistrent automatiquement la structure : fichiers créés ou modifiés, imports entre fichiers (JS/TS, Python, et `src`/`href`/`@import`/`url()` en HTML et CSS), agents, skills et commandes invoqués, sessions, commandes Bash (secrets masqués). Tu n'as pas à le faire à la main. Ta responsabilité : interroger le graphe avant d'agir, et y ajouter les faits durables que les hooks ne peuvent pas deviner.

## 1. Commandes

- Interroger : `python3 .claude/hooks/graph_hook.py query <terme>` (chemin, nom d'agent, nom de skill, sujet)
- Ajouter un fait : `python3 .claude/hooks/graph_hook.py note <sujet> "<fait court et vérifiable>"`
- Réindexer tout le projet (après un gros déplacement) : `python3 .claude/hooks/graph_hook.py index`
- Ne jamais éditer `graph.json` à la main. Passer uniquement par ces commandes.

## 2. Au démarrage de chaque session

1. Lire `.claude/memory/etat.md` (règles du protocole mémoire texte).
2. Interroger le graphe sur le sujet de la tâche demandée.
3. Annoncer en 3 lignes maximum : l'état, les fichiers et agents/skills concernés, la prochaine étape.

## 3. Avant de modifier un fichier

- Lancer `query <chemin>` pour voir ce qui l'importe (`IMPORTS`) et qui l'a déjà touché (`TOUCHED`).
- Si un fichier importé est impacté, le signaler avant de continuer.
- Un fichier sans dépendant connu n'est pas forcément inutile : vérifier avec `grep` avant de le supprimer.

## 4. Agents, skills, commandes et hooks

Ces dossiers sont la configuration du projet. Traite-les avec plus de soin que le code applicatif.

- **Avant de créer ou modifier** un agent (`.claude/agents/`), une skill (`.claude/skills/`), une commande (`.claude/commands/`) ou un hook (`.claude/hooks/`) : `query <nom>` pour vérifier qu'il n'existe pas déjà ou qu'un élément similaire ne fait pas le même travail.
- **Après** : `note <nom-de-l-élément> "<rôle en une phrase, déclencheurs, outils autorisés>"`.
- Une skill ou un agent doit toujours avoir un rôle unique. Si deux éléments se chevauchent, le signaler à l'utilisateur plutôt que de créer un doublon.
- Ne jamais modifier `settings.json` pour désactiver un hook sans demander la permission explicite de l'utilisateur.

## 5. Ce qui mérite un `note`

Ajoute un fait au graphe (`note`) dès qu'il est durable et vérifiable :
- une règle métier ou une contrainte technique (`note auth "les tokens expirent après 24 h, refresh via /api/v1/refresh"`) ;
- une dépendance cachée entre deux parties du projet ;
- une décision d'architecture, avec le fichier ou le sujet concerné ;
- un agent ou une skill ajouté, supprimé ou renommé ;
- une commande de déploiement ou de migration, avec son effet.

Ne pas noter : les états temporaires, les hypothèses non vérifiées, les secrets, les données personnelles ou clients.

## 6. Cohérence entre les mémoires

- Quand une décision apparaît à la fois dans `.claude/memory/decisions.md` et dans le graphe, les deux doivent rester cohérents. En cas de contradiction, demander à l'utilisateur laquelle est à jour.
- Si un fichier ou un agent disparaît du dépôt, le signaler : le graphe garde l'ancien nœud jusqu'à la prochaine revue.

## 7. Reprise après interruption

Après un crash ou une nouvelle session, la reprise se fait dans cet ordre : `etat.md`, puis `query` sur les fichiers listés comme « en cours », puis `git status`. Ne rejoue aucune action marquée « en cours » sans avoir vérifié son résultat réel.

## 8. Règles de qualité

- Les faits notés doivent être concrets : chemins, noms exacts, commandes complètes.
- Pas de secrets dans les notes. Utiliser des noms de variables d'environnement.
- Le graphe décrit l'état du projet, pas l'historique. L'historique reste dans `journal.md` et dans git.
