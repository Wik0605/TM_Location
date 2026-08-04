# Étape 1 — Compression Gzip & Cache HTTP statique

Date : 2026-08-04
Fichier modifié : `app/main.py`

## Objectif

Réduire le poids téléchargé par les navigateurs (surtout mobiles) et éviter le
re-téléchargement inutile des fichiers statiques (CSS, JS, images) entre les
visites. Aucune dépendance ajoutée, aucun changement de comportement métier.

## Ce qui a été fait

### 1. Middleware Gzip

Ajout de `GZipMiddleware` (fourni par Starlette, déjà inclus avec FastAPI) :

```python
from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

- Compresse automatiquement toute réponse HTTP > 1 KB si le client envoie
  l'en-tête `Accept-Encoding: gzip` (tous les navigateurs modernes le font).
- Gain typique : **70 à 80 %** sur le HTML, CSS, JS et JSON.
- Aucun effet sur les images/fonts (déjà compressés).

### 2. Cache HTTP sur `/static`

Création d'une sous-classe légère de `StaticFiles` qui ajoute l'en-tête
`Cache-Control` sur chaque fichier servi :

```python
class CachedStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, Response) and response.status_code == 200:
            response.headers["Cache-Control"] = (
                f"public, max-age={STATIC_CACHE_MAX_AGE}"
            )
        return response
```

- `STATIC_CACHE_MAX_AGE = 60 * 60 * 24 * 7` → **7 jours**.
- Le navigateur conserve les fichiers en cache local pendant une semaine :
  la 2ᵉ visite ne redemande plus le CSS/JS/images.
- Le montage `/static` utilise maintenant cette classe :

```python
app.mount("/static", CachedStaticFiles(directory=str(STATIC_DIR)), name="static")
```

## Comment vérifier

Lancer l'app :

```
uvicorn app.main:app --reload
```

Puis dans un autre terminal :

```
curl -I -H "Accept-Encoding: gzip" http://localhost:8000/static/dist.css
```

Réponse attendue :

- `content-encoding: gzip`
- `cache-control: public, max-age=604800`

## Impact attendu

- **Première visite** : téléchargement plus léger (gzip sur HTML/CSS/JS).
- **Visites suivantes** : les fichiers statiques ne sont plus re-téléchargés
  pendant 7 jours → chargement quasi instantané.
- Bénéfice particulièrement fort sur mobile 3G / réseau lent.

## À noter

- Si un fichier statique change, il faut invalider le cache. Deux options
  possibles à l'avenir :
  - Ajouter un hash dans le nom du fichier (`dist.abc123.css`) — méthode
    standard mais demande un pipeline de build.
  - Utiliser un query-string versionné (`dist.css?v=2`) dans les templates.
- Pour l'instant, en dev, un `Cmd+Shift+R` force le rechargement.

## Prochaine étape

Étape 2 du plan : **purger Tailwind** pour faire tomber `dist.css` de 2,45 MB
à moins de 50 KB.
