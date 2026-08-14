# Workflow de développement TM_Location

Guide pratique pour ajouter, tester et déployer une nouvelle feature sans casser la production.

## Vue d'ensemble

```
1. Créer une branche Git         (isolation du code)
2. Coder en local avec .env.dev  (bac à sable perso)
3. Tester en local               (http://localhost:8000)
4. Push la branche               (Railway crée preview auto)
5. Tester sur preview URL        (conditions cloud réelles)
6. Merger vers main              (déploiement en prod)
7. Nettoyer la branche
```

## Les 3 environnements

| Environnement | URL | Base de données | Usage |
|---|---|---|---|
| **Dev local** | http://localhost:8000 | SQLite `data/*.db` | Développement quotidien |
| **Preview Railway** | https://tmlocation-feature-xxx.up.railway.app | Isolée par branche | Test avant merge |
| **Production** | https://tondomaine.com | PostgreSQL / SQLite Railway | Users réels |

## Prérequis

- `.env.dev` présent à la racine (créé lors du setup, non commité)
- Environnement virtuel activé : `source venv/bin/activate`
- Preview Environments activés dans Railway (Settings → Environments)

---

## Étape 1 — Créer une branche

```bash
git checkout main
git pull
git checkout -b feature/nom-clair
```

Convention de nommage :
- `feature/xxx` : nouvelle fonctionnalité
- `fix/xxx` : correction de bug
- `refactor/xxx` : réorganisation de code

## Étape 2 — Coder en local

Lancer l'app locale :

```bash
python run.py
```

Sortie attendue :

```
[dev] variables chargees depuis .env.dev
INFO: Uvicorn running on http://0.0.0.0:8000
```

Pour rechargement automatique à chaque sauvegarde :

```bash
uvicorn app.main:app --reload
```

Reset de la base locale si besoin :

```bash
rm data/*.db
python -m alembic upgrade head
```

## Étape 3 — Tester en local

Ouvrir http://localhost:8000 et vérifier :

- La feature fonctionne
- Les features existantes ne sont pas cassées
- Aucune erreur dans le terminal
- Rendu mobile OK (DevTools → mode responsive)

## Étape 4 — Push la branche

```bash
git status
git diff
git add <fichiers modifies>
git commit -m "feat(module): description courte"
git push -u origin feature/nom-clair
```

Railway déploie automatiquement une URL de preview visible dans le dashboard.

## Étape 5 — Tester sur preview URL

Ouvrir l'URL preview générée. Vérifier en priorité :

- HTTPS fonctionne
- OAuth Google fonctionne (nécessite HTTPS)
- Uploads persistants
- Performance sur mobile réel

Si un bug est trouvé, corriger en local, re-push : Railway met à jour la même URL preview.

## Étape 6 — Merger vers main

### Option A — Ligne de commande

```bash
git checkout main
git pull
git merge feature/nom-clair
git push
```

### Option B — Pull Request GitHub (recommandé)

```bash
gh pr create --title "feat: description" --body "Details de la feature"
```

Puis merger via l'interface GitHub après review.

Le push sur `main` déclenche le déploiement production automatique (2-3 min).

## Étape 7 — Nettoyer

```bash
git branch -d feature/nom-clair
git push origin --delete feature/nom-clair
```

---

## Règles absolues

1. **Jamais commiter directement sur `main`** : toujours passer par une branche
2. **Jamais toucher la DB de prod depuis le local** : `.env.dev` pointe uniquement vers SQLite locale
3. **Toujours tester la preview avant merge** : comportement local ≠ cloud
4. **Une branche = une feature** : pas de branches fourre-tout
5. **Commits descriptifs** : `feat(favoris): ajoute bouton coeur` plutôt que `wip`

## Convention de messages de commit

Format : `type(scope): description`

Types courants :
- `feat` : nouvelle fonctionnalité
- `fix` : correction de bug
- `refactor` : réorganisation sans changement de comportement
- `docs` : documentation
- `style` : formatage, indentation
- `chore` : tâches diverses (deps, config)

Exemples :
```
feat(favoris): ajoute modele Favorite
fix(auth): corrige redirection apres login Google
refactor(recherche): extrait logique de filtres
docs: ajoute WORKFLOW.md
```

## Rollback en cas de bug en production

### Solution 1 — Revert Git

```bash
git checkout main
git revert HEAD
git push
```

### Solution 2 — Rollback Railway

Dashboard Railway → onglet **Deployments** → sélectionner un ancien déploiement fonctionnel → **Redeploy**.

## Cheatsheet

```bash
# Démarrer une feature
git checkout main && git pull
git checkout -b feature/nom-clair
python run.py

# Pendant le dev
git add .
git commit -m "feat(x): message clair"

# Push pour tester en cloud
git push -u origin feature/nom-clair

# Une fois validé
git checkout main
git merge feature/nom-clair
git push

# Nettoyage
git branch -d feature/nom-clair
git push origin --delete feature/nom-clair
```
