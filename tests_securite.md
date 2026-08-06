# Tests de sécurité — TM_Location

Guide pas-à-pas pour valider manuellement les 14 fixes appliqués (voir `securite_handlung.md`).

## Préparation

```
uvicorn app.main:app --reload
```

Puis ouvrir le navigateur sur `http://localhost:8000`.

Ouvre aussi la console DevTools (F12 → onglet **Network** et **Console**), tu en auras besoin pour plusieurs tests.

Garde un œil sur le terminal `uvicorn` : les logs `WARNING security ...` doivent apparaître à chaque tentative bloquée.

---

## 1. Auth admin centralisée (fix #1)

**Action** : sans être connecté, essaie d'aller directement sur chacune de ces URL dans le navigateur :
- `http://localhost:8000/admin`
- `http://localhost:8000/admin/voitures`
- `http://localhost:8000/admin/reservations`

**Comportement attendu** : les 3 URL redirigent vers `/admin/login`. Aucune ne s'affiche sans session.

---

## 2. Rate limit sur le login admin (fix #2)

**Action** :
1. Va sur `/admin/login`.
2. Tape un mauvais mot de passe et clique "Se connecter".
3. Répète **5 fois de plus** avec un mauvais mot de passe (donc 6 tentatives au total).

**Comportement attendu** :
- Tentatives 1 à 5 : la page se recharge avec le message "Identifiant ou mot de passe incorrect."
- Tentative 6 (et suivantes pendant 15 min) : page avec le message **"Trop de tentatives. Réessayez dans quelques minutes."** (status HTTP 429 visible dans Network).
- Dans le terminal : tu vois **5 lignes** `WARNING security admin_login_failure user=... ip=127.0.0.1` puis **1 ligne** `WARNING security rate_limit_exceeded path=/admin/login`.

**Reset** : attendre 15 min OU redémarrer `uvicorn`.

---

## 3. Login admin qui marche + logs (fix #13)

**Action** : après reset du rate limit, connecte-toi avec les bons identifiants (`tafita` / le mdp de ton `.env`).

**Comportement attendu** :
- Redirection vers `/admin` (dashboard).
- Terminal : `INFO security admin_login_success user=tafita ip=127.0.0.1`.

---

## 4. Rotation de session au login (fix #5)

**Action** :
1. DevTools → **Application** → **Cookies** → `http://localhost:8000`.
2. Note la valeur du cookie `session` avant login.
3. Va sur `/admin/login` (ça pose un nouveau cookie s'il n'y en a pas).
4. Note à nouveau la valeur du cookie.
5. Connecte-toi avec les bons identifiants.
6. Note une 3ᵉ fois la valeur.

**Comportement attendu** : la valeur du cookie **change** après login réussi. C'est la rotation de session (protège contre session fixation).

---

## 5. Protection CSRF sur `/admin/login` (fix #14)

**Action** :
1. Ouvre `/admin/login` dans le navigateur.
2. DevTools → **Console** → colle et exécute :
   ```javascript
   fetch('/admin/login', {
     method: 'POST',
     headers: {'Content-Type': 'application/x-www-form-urlencoded'},
     body: 'username=x&password=y'
   }).then(r => console.log('status:', r.status));
   ```

**Comportement attendu** : `status: 403`. La console dit 403 car le champ `csrf_token` manque.

**Ensuite** : essaie de te connecter **normalement via le formulaire**. Ça doit marcher (le formulaire inclut `{{ csrf_input(request) }}` automatiquement).

---

## 6. Protection CSRF sur `/reserver` (fix #14)

**Action** :
1. Ouvre une page voiture, ex. `http://localhost:8000/voitures/1`.
2. DevTools → **Console** :
   ```javascript
   fetch('/voitures/1/reserver', {
     method: 'POST',
     headers: {'Content-Type': 'application/x-www-form-urlencoded'},
     body: 'client_nom=hack&client_telephone=000&date_debut=2026-01-01'
   }).then(r => console.log('status:', r.status));
   ```

**Comportement attendu** : `status: 403`.

**Ensuite** : remplis le vrai formulaire de réservation dans la page. Ça doit passer.

---

## 7. Protection CSRF sur HTMX admin (fix #14)

**Action** : une fois connecté admin, va sur `/admin/voitures` et clique sur "Supprimer" ou "Modifier" une voiture.

**Comportement attendu** : l'action fonctionne normalement. Vérifie dans DevTools → **Network** → clique sur la requête HTMX (`POST /admin/voitures/.../delete`) → **Headers** → tu dois voir l'en-tête **`X-CSRF-Token: ...`** envoyé automatiquement.

---

## 8. Rate limit sur `/reserver` (fix #10)

**Action** : dans la console DevTools (une fois sur `/voitures/1`), boucle 11 fois :
```javascript
const token = document.querySelector('input[name=csrf_token]').value;
for (let i = 1; i <= 12; i++) {
  const r = await fetch('/voitures/1/reserver', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: `client_nom=x&client_telephone=1&date_debut=2026-01-01&csrf_token=${token}`
  });
  console.log(`tentative ${i}: ${r.status}`);
}
```

**Comportement attendu** : les 10 premières donnent `200` (ou `400`/`422` si validation Pydantic échoue, mais pas 429). La 11ᵉ et 12ᵉ donnent `429`.

---

## 9. Rate limit sur `/auth/google` (fix #10)

**Action** : recharge 21 fois `http://localhost:8000/auth/google` (F5).

**Comportement attendu** : les 20 premières redirigent vers Google. La 21ᵉ affiche **"Trop de requêtes. Réessayez dans quelques minutes."**

---

## 10. OAuth Google — CSRF `state` (fix #8)

**Action** : sans passer par `/auth/google`, visite directement :
```
http://localhost:8000/auth/google/callback?code=fakecode&state=fakestate
```

**Comportement attendu** : erreur `400 État OAuth invalide.` (ou une page 400).
Terminal : `WARNING security oauth_state_mismatch ip=127.0.0.1`.

---

## 11. OAuth Google — config manquante (fix #8)

**Action** : temporairement, vide `GOOGLE_CLIENT_ID` dans `.env` (mets `GOOGLE_CLIENT_ID=`), redémarre `uvicorn`, puis va sur `/auth/google`.

**Comportement attendu** : `503 Connexion Google indisponible (configuration manquante).`

**N'oublie pas** de restaurer ta clé après le test.

---

## 12. Security headers (fix #9)

**Action** : ouvre n'importe quelle page (ex. `/`), DevTools → **Network** → clique sur la requête principale → **Headers** → section **Response Headers**.

**Comportement attendu** : tu vois ces 4 en-têtes :
- `x-content-type-options: nosniff`
- `x-frame-options: DENY`
- `referrer-policy: strict-origin-when-cross-origin`
- `permissions-policy: geolocation=(self), microphone=(), camera=()`

Note : `Strict-Transport-Security` n'apparaît **pas** en dev (normal, il n'est posé qu'en prod).

**Bonus clickjacking** : crée un fichier `test.html` :
```html
<iframe src="http://localhost:8000/admin" width="800" height="600"></iframe>
```
Ouvre-le. L'iframe doit **rester vide** (bloqué par `X-Frame-Options: DENY`).

---

## 13. Upload d'image bornée (fix #12)

**Action** : dans l'admin, sur une voiture, essaie d'uploader :
- **A.** une image normale (< 8 MB) → doit passer.
- **B.** un fichier > 8 MB (crée-le : `dd if=/dev/urandom of=big.jpg bs=1M count=10`). Attention, ce n'est pas une vraie image, Pillow refusera de le décoder → skip silencieux.
- **C.** un vrai gros JPEG (> 8 MB) → la limite de taille kick in avant décodage, skip silencieux.

**Comportement attendu** : dans les cas B et C, la voiture affiche uniquement les images des autres uploads réussis. Pas d'erreur 500, pas de crash.

---

## 14. Crash en prod si secrets par défaut (fix #4)

**Action** : dans un terminal séparé, lance en prod avec un secret vide :
```
ENVIRONMENT=production SECRET_KEY=changeme uvicorn app.main:app
```

**Comportement attendu** : l'app **refuse de démarrer** avec :
```
RuntimeError: Configuration de production non securisee:
  - SECRET_KEY doit etre defini et faire au moins 32 caracteres
  - ADMIN_PASSWORD doit etre defini et faire au moins 12 caracteres
```

**Test inverse** : avec de bonnes valeurs :
```
ENVIRONMENT=production SECRET_KEY=$(openssl rand -hex 32) ADMIN_PASSWORD=$(openssl rand -base64 24) uvicorn app.main:app
```
→ démarrage normal.

---

## 15. HSTS en prod (fix #9)

**Action** : même commande de lancement en prod (précédente), puis `curl -I http://localhost:8000/` dans un autre terminal.

**Comportement attendu** : la réponse contient `strict-transport-security: max-age=31536000; includeSubDomains`.

---

## 16. Bonus — Tests d'attaque migration carte (jamais faits)

Ces tests sont documentés dans `Carte_migration.md`. À valider aussi puisqu'on est dans le durcissement :

- **Distance forcée** : ouvre `/voitures/1`, calcule un itinéraire, puis DevTools → modifie la valeur `<input name="itinerary_distance_km">` à `999999`, soumets. Attendu : le back ignore et utilise sa distance mémorisée du token.
- **Token forgé** : modifie `<input name="itinerary_token">` à `fakefake`, soumets. Attendu : distance = 0 ou absente (le back n'a pas trouvé le token).
- **Token expiré** : calcule un itinéraire, attends 16 min, puis soumets. Attendu : token invalide côté back.

---

## Checklist de fin

- [ ] Test 1 — Auth admin OK
- [ ] Test 2 — Rate limit login OK
- [ ] Test 3 — Login réussi + log OK
- [ ] Test 4 — Rotation session OK
- [ ] Test 5 — CSRF login OK
- [ ] Test 6 — CSRF reserver OK
- [ ] Test 7 — CSRF HTMX admin OK
- [ ] Test 8 — Rate limit reserver OK
- [ ] Test 9 — Rate limit OAuth OK
- [ ] Test 10 — CSRF OAuth state OK
- [ ] Test 11 — OAuth config manquante OK
- [ ] Test 12 — Security headers OK
- [ ] Test 13 — Upload bornée OK
- [ ] Test 14 — Crash prod secrets par défaut OK
- [ ] Test 15 — HSTS en prod OK
- [ ] Test 16 — Attaques carte OK

Si un test échoue, note lequel et le comportement observé — on debug ensemble.
