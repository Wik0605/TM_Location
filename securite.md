# Audit de Sécurité - TM_Location

**Date** : 28 juillet 2026
**Version** : 1.0
**Statut** : ⚠️ Critique - Correction urgente requise

---

## 📋 Résumé Exécutif

L'audit a identifié **10 vulnérabilités** dans l'application TM_Location, dont **4 critiques** permettant une prise de contrôle totale du système. L'application est actuellement vulnérable à des attaques courantes (CSRF, SQL Injection, vol de sessions) en raison de configurations par défaut non sécurisées et de secrets exposés.

**Risque global** : ⚠️⚠️⚠️ **Élevé** (Exploitation triviale possible)

---

## 🔍 Vulnérabilités Critiques (À corriger immédiatement)

### 1. **Secrets par défaut exposés** (`app/config.py`)
- **Problème** : 
  - Clé secrète : `"changeme"`
  - Identifiants admin : `"admin"` / `"admin"`
  - Ces valeurs sont **commises dans Git**.
- **Impact** : 
  - Prise de contrôle complète de l'espace admin.
  - Falsification de sessions utilisateur.
- **Preuve** :
  ```python
  # app/config.py:5-7
  secret_key: str = "changeme"
  admin_username: str = "admin"
  admin_password: str = "admin"
  ```

### 2. **CORS trop permissif** (`app/main.py`)
- **Problème** :
  ```python
  allow_origins=["*"]  # Tous les domaines autorisés
  allow_credentials=True  # + Cookies = Danger
  ```
- **Impact** :
  - Un site malveillant (ex: `evil.com`) peut voler des données ou effectuer des actions au nom de l'utilisateur (CSRF).
  - Vol de cookies de session via JavaScript.

### 3. **Injection SQL potentielle** (`app/routers/web.py`)
- **Problème** :
  ```python
  # Ligne 98 : Pas de validation de date_debut
  start = datetime.datetime.strptime(date_debut, "%Y-%m-%d")
  ```
- **Impact** :
  - Corruption/vol de données via des payloads malveillants (ex: `"2023-01-01; DROP TABLE locations"`).

### 4. **Clés Google OAuth exposées** (`.env`)
- **Problème** :
  - `GOOGLE_CLIENT_ID` et `GOOGLE_CLIENT_SECRET` sont **dans Git**.
  - Historique accessible via `git log`.
- **Impact** :
  - Usurpation d'identité de l'application.
  - Vol de données utilisateur (emails, profils Google).

---

## 📊 Tableau des Risques

| Niveau       | Vulnérabilité                          | Impact Potential                     | Exploitable ? |
|--------------|----------------------------------------|--------------------------------------|---------------|
| ⚠️ Critique   | Secrets par défaut                     | Prise de contrôle admin               | ✅ Oui        |
| ⚠️ Critique   | CORS mal configuré                     | CSRF / Vol de sessions                | ✅ Oui        |
| ⚠️ Élevé      | Injection SQL                          | Corruption de la base                | ⚠️ Possible   |
| ⚠️ Élevé      | Clés OAuth exposées                    | Vol de données utilisateur           | ✅ Oui        |
| ⚠️ Moyen      | Sessions non sécurisées                | Session hijacking                    | ✅ Oui        |
| ⚠️ Moyen      | Uploads non contrôlés                  | Exécution de code arbitraire         | ⚠️ Possible   |

---

## 🛡️ Plan de Correction (Priorisé)

### 🔴 **Phase 1 : Urgent (À faire aujourd'hui)**
1. **Changer tous les secrets** :
   - Générer une `SECRET_KEY` forte :
     ```bash
     openssl rand -hex 32
     ```
   - Modifier `ADMIN_USERNAME`/`ADMIN_PASSWORD` dans `.env`.
   - **Supprimer `.env` de Git** :
     ```bash
     git rm --cached .env
     echo ".env" >> .gitignore
     ```

2. **Restreindre le CORS** :
   ```python
   # Remplacer dans app/main.py
   allow_origins=["https://votre-domaine.com"],  # Liste blanche
   allow_credentials=False,  # Désactiver si pas nécessaire
   ```

3. **Sécuriser les sessions** :
   ```python
   app.add_middleware(
       SessionMiddleware,
       secret_key=settings.secret_key,
       https_only=True,
       same_site="lax",
       max_age=3600
   )
   ```

4. **Valider les entrées** :
   - Utiliser Pydantic pour tous les formulaires.
   - Exemple pour `date_debut` :
     ```python
     from pydantic import BaseModel, field_validator
     from datetime import datetime
     
     class ReservationForm(BaseModel):
         date_debut: str
         
         @field_validator('date_debut')
         def validate_date(cls, v):
             try:
                 return datetime.strptime(v, "%Y-%m-%d")
             except ValueError:
                 raise ValueError("Format de date invalide")
     ```

### 🟡 **Phase 2 : Important (Sous 1 semaine)**
5. **Régénérer les clés Google OAuth** :
   - Aller dans [Google Cloud Console](https://console.cloud.google.com/).
   - Créer de nouvelles clés et restreindre les URIs de redirection.

6. **Sécuriser les uploads** :
   - Limiter les extensions (`.jpg`, `.png`).
   - Déplacer `static/uploads/` hors du répertoire web.

7. **Ajouter des en-têtes de sécurité** :
   ```python
   from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
   from fastapi.middleware.trustedhost import TrustedHostMiddleware
   
   app.add_middleware(HTTPSRedirectMiddleware)
   app.add_middleware(TrustedHostMiddleware, allowed_hosts=["votre-domaine.com"])
   ```

### 🟢 **Phase 3 : Recommandations (Améliorations)**
8. **Activer HTTPS** :
   - Utiliser Let's Encrypt avec Certbot.

9. **Audit des dépendances** :
   ```bash
   pip install safety
   safety check
   ```

10. **Tests de pénétration** :
    - Utiliser [OWASP ZAP](https://www.zaproxy.org/) pour scanner l'application.

---

## 🎯 Checklist de Sécurité Post-Correction

- [ ] Tous les secrets sont **hors de Git** et uniques.
- [ ] Le CORS est restreint à une liste blanche.
- [ ] Les cookies sont sécurisés (`httponly`, `secure`, `samesite`).
- [ ] Toutes les entrées utilisateur sont validées.
- [ ] Les clés OAuth sont régénérées et restreintes.
- [ ] Les uploads sont contrôlés et isolés.
- [ ] HTTPS est activé en production.

---

## 📚 Ressources Utiles
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) (Guide des vulnérabilités web).
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/) (Documentation officielle).
- [Mozilla SSL Config Generator](https://ssl-config.mozilla.org/) (Configuration HTTPS).

---

**Prochaine étape** : Appliquer les corrections de la **Phase 1** immédiatement, puis planifier les phases suivantes.

> ⚠️ **Avertissement** : Ne déployez pas l'application en production tant que les failles critiques ne sont pas corrigées.
