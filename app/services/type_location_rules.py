"""Règles de croisement entre TypeLocation et plage horaire réservée.

Les noms de TypeLocation sont libres. On reconnaît un type par mot-clé
présent dans son nom (insensible à la casse et aux accents).
"""

from datetime import datetime
from unicodedata import normalize


def _normaliser(texte: str) -> str:
    sans_accents = normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return sans_accents.lower()


# Chaque règle : mots-clés à chercher dans le nom + contraintes horaires.
# - heure_debut_min / heure_debut_max : bornes (incluses) de l'heure de départ
# - duree_h : durée exacte attendue (en heures)
# - duree_min_h / duree_max_h : bornes (incluses) de la durée
RULES = [
    {
        "keywords": ["demi", "1/2"],
        "libelle": "1/2 journée",
        "heure_debut_min": 6,
        "heure_debut_max": 12,
        "duree_h": 6,
    },
    {
        "keywords": ["journee", "journée"],
        "libelle": "journée",
        "heure_debut_min": 6,
        "heure_debut_max": 10,
        "duree_min_h": 8,
        "duree_max_h": 10,
    },
    {
        "keywords": ["10h-14h", "creneau", "créneau"],
        "libelle": "créneau 10h-14h",
        "heure_debut_min": 10,
        "heure_debut_max": 10,
        "duree_h": 4,
    },
]


def _trouver_regle(nom: str) -> dict | None:
    nom_norm = _normaliser(nom)
    for regle in RULES:
        for kw in regle["keywords"]:
            if _normaliser(kw) in nom_norm:
                return regle
    return None


def valider_type_location(nom: str, debut: datetime, fin: datetime) -> None:
    """Vérifie que la plage [debut, fin] respecte les contraintes du type.

    Lève ValueError si la plage est incompatible. Ne fait rien si le nom
    ne matche aucune règle (type custom sans contrainte).
    """
    regle = _trouver_regle(nom)
    if regle is None:
        return

    h = debut.hour
    if not (regle["heure_debut_min"] <= h <= regle["heure_debut_max"]):
        raise ValueError(
            f"Pour un type « {regle['libelle']} », l'heure de début doit être "
            f"entre {regle['heure_debut_min']}h et {regle['heure_debut_max']}h "
            f"(reçu : {h}h)."
        )

    duree_h = (fin - debut).total_seconds() / 3600
    if "duree_h" in regle:
        if abs(duree_h - regle["duree_h"]) > 0.01:
            raise ValueError(
                f"Pour un type « {regle['libelle']} », la durée doit être "
                f"exactement de {regle['duree_h']}h (reçu : {duree_h:.1f}h)."
            )
    else:
        mn, mx = regle["duree_min_h"], regle["duree_max_h"]
        if not (mn <= duree_h <= mx):
            raise ValueError(
                f"Pour un type « {regle['libelle']} », la durée doit être "
                f"entre {mn}h et {mx}h (reçu : {duree_h:.1f}h)."
            )
