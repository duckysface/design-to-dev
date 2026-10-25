# Protocole de mémoire projet (OBLIGATOIRE)

Ce projet utilise un dossier de mémoire versionné dans `.claude/memory/`.
Cette mémoire est la seule source de vérité entre les sessions. Ce qui n'est pas écrit dans ces fichiers est considéré comme perdu : une session peut tomber à tout moment, et la suivante doit pouvoir reprendre le projet sans aucune perte.

## 1. Structure

```
.claude/memory/
├── MEMORY.md        # Index du projet : résumé + liens vers les autres fichiers (< 150 lignes)
├── etat.md          # ÉTAT COURANT : où on en est, quoi faire ensuite (mis à jour très souvent)
├── journal.md       # Journal chronologique, APPEND-ONLY (jamais de réécriture de l'historique)
├── changements.md   # Registre de chaque fichier créé, modifié, déplacé ou supprimé
├── decisions.md     # Choix techniques et leurs raisons
├── problemes.md     # Erreurs, bugs, pièges rencontrés et solutions trouvées
└── archives/        # Anciennes entrées de journal, déplacées pour garder les fichiers légers
```

Créer les fichiers manquants dès le début de la session, avec un en-tête court.

## 2. Au démarrage de CHAQUE session

1. Lire `MEMORY.md`, puis `etat.md` en entier, puis les 60 dernières lignes de `journal.md`.
2. Si le projet est un dépôt git : lancer `git status` et `git diff --stat`.
3. Comparer l'état réel (fichiers, git) avec `etat.md`.
   - Si tout est cohérent : annoncer en 3 lignes maximum où on en est et la prochaine étape, puis continuer.
   - Si une incohérence existe (fichier modifié non noté, étape marquée « en cours » qui semble terminée ou non commencée) : le signaler et demander confirmation avant d'agir.
4. Ajouter une entrée de début de session dans `journal.md`.

## 3. Quand écrire en mémoire (déclencheurs obligatoires)

Mettre à jour la mémoire, sans attendre la fin de la tâche, à chaque fois que :

- un fichier est **créé, modifié, renommé, déplacé ou supprimé** ;
- une commande **a un effet** (installation de dépendances, migration, build, déploiement, commit, suppression, appel d'API qui écrit) ;
- une **décision** est prise (ou validée par l'utilisateur) ;
- une **erreur** ou un piège est rencontré, même si résolu rapidement ;
- une étape du plan est **terminée**, ou un **nouveau plan** est défini ;
- l'utilisateur **change de sujet**, demande une **pause**, ou la session **se termine** ;
- une **information durable** sur le projet ou sur l'utilisateur est apprise (préférences, contraintes, accès, conventions).

Règle d'ordre pour les actions non triviales :
- **AVANT** : écrire dans `etat.md` l'action prévue et son statut « EN COURS ».
- **APRÈS** : écrire le résultat dans `changements.md` et `journal.md`, puis mettre `etat.md` à jour.

Cela garantit qu'une session interrompue au milieu d'une action reste reprenable.

## 4. Format des entrées

**changements.md** (une ligne par fichier touché) :
```
- [AAAA-MM-JJ HH:MM] MODIFIÉ `src/api/users.ts` — ajout de la validation d'email (tâche : inscription)
- [AAAA-MM-JJ HH:MM] CRÉÉ `tests/users.test.ts` — tests de la validation
- [AAAA-MM-JJ HH:MM] SUPPRIMÉ `src/old/helper.ts` — remplacé par `src/utils/format.ts`
```

**journal.md** (une entrée par bloc de travail) :
```
## AAAA-MM-JJ HH:MM — Session [id court] — [sujet]
- Objectif : ...
- Fait : ...
- Commandes importantes lancées : ... (avec résultat)
- Problèmes : voir problemes.md#[titre]
- Décisions : voir decisions.md#[titre]
```

**decisions.md** :
```
## [Titre court] (AAAA-MM-JJ)
- Décision : ...
- Raison : ...
- Alternatives écartées : ...
- Validée par : utilisateur / Claude
```

**problemes.md** :
```
## [Symptôme court] (AAAA-MM-JJ)
- Contexte : ...
- Cause : ...
- Solution : ...
- À ne pas refaire : ...
```

## 5. etat.md : le fichier de reprise (le plus important)

`etat.md` doit toujours être réécrit complètement (pas seulement complété) avec ce modèle :

```
# État courant — mis à jour le AAAA-MM-JJ HH:MM

## Objectif global
[Ce que le projet doit accomplir, en 1-3 lignes]

## Tâche en cours
[Nom de la tâche] — statut : EN COURS | BLOQUÉE | EN ATTENTE DE VALIDATION

## Fait récemment
- ...

## Prochaine étape exacte
[Action précise, assez détaillée pour être exécutée sans contexte supplémentaire]

## Action en cours au moment de l'arrêt (si applicable)
- Commande / modification : ...
- Fichiers concernés : ...
- Résultat connu : terminé | partiel | non commencé

## Commandes pour reprendre
- Installer : ...
- Lancer / tester : ...

## Fichiers clés touchés dans cette tâche
- ...

## Questions ouvertes pour l'utilisateur
- ...

## Points de vigilance
- ...
```

## 6. Passation et reprise après interruption

- **Fin de session ou pause demandée** : mettre à jour `etat.md` complètement, ajouter une entrée de fin dans `journal.md`, puis résumer en 5 lignes maximum ce qui a été fait et ce qui reste.
- **Reprise après crash** : si `etat.md` indique une action « EN COURS » sans résultat connu, vérifier l'état réel (`git diff`, contenu des fichiers concernés) avant de la relancer. Ne jamais rejouer une commande destructive ou non idempotente sans confirmation.
- **Aucune réponse n'est une réponse** : si une information n'est pas dans la mémoire ni dans le code, la demander à l'utilisateur plutôt que de la deviner.

## 7. Règles de qualité

- Écrire de façon concrète et vérifiable : chemins exacts, noms de fonctions, commandes complètes, dates.
- Ne jamais écrire de secrets (mots de passe, clés API, tokens, chaînes de connexion, données clients). Utiliser des noms de variables d'environnement.
- Ne pas dupliquer le contenu de la documentation externe : écrire seulement ce qui est propre à ce projet.
- Garder `MEMORY.md` sous 150 lignes. Quand `journal.md` dépasse environ 400 lignes, déplacer les entrées les plus anciennes dans `archives/journal-AAAA-MM.md`.
- Ne jamais réécrire ni supprimer une entrée de `journal.md` : pour corriger, ajouter une nouvelle entrée.
- Quand un fichier est ajouté au dossier mémoire, l'ajouter à la liste de `MEMORY.md`.

## 8. Confirmation

Après chaque mise à jour importante de la mémoire, ajouter une ligne discrète du type : « 📝 Mémoire mise à jour (etat.md, changements.md) ». Ne pas détailler le contenu sauf si l'utilisateur le demande.

## 9. Ce que cette mémoire ne remplace pas

Cette mémoire ne remplace pas `git`. Les modifications de code doivent quand même être commitées avec des messages clairs. La mémoire décrit le *pourquoi* et l'*où on en est* ; git garde le *quoi exactement*.
