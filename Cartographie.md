Cartographie TM  Location 
Le nouveau flux (concept)

  Aujourd'hui :
  Client clique "Calculer"
    → JS appelle brouter.de
    → JS reçoit distance
    → JS affiche + stocke dans <input hidden>
    → POST /reserver avec distance (falsifiable)

  Nouvelle approche :
  Client clique "Calculer"
    → JS envoie SEULEMENT les waypoints à ton back
    → FastAPI appelle brouter.de côté serveur
    → FastAPI renvoie {distance, polyline, prix_estimé}
    → JS affiche le résultat
    → POST /reserver : le back RECALCULE (ou récupère depuis
  cache/session)
  
  La clé : le client n'envoie jamais un nombre, il envoie des 
  points GPS. Le serveur est seul maître du calcul de distance.

  Les 5 défis techniques réels

  1. 🐢 Latence perçue par l'utilisateur

  Avant : navigateur → brouter.de = 1 saut (~400ms)
  Après : navigateur → ton VPS → brouter.de → ton VPS → 
  navigateur = 2 sauts (~700-900ms)

  Solution : afficher un spinner pendant le calcul + cacher les
   résultats côté back (Redis ou dict en mémoire). Deux clients
   qui calculent Tana→Antsirabe = 1 seul appel à brouter, tous
  les suivants sont instantanés.

  ---
  2. 🔄 Cohérence entre "affiché" et "facturé"

  Piège classique : le back calcule 127 km à 14h00, l'affiche
  au client. Le client réserve à 14h05. Entre-temps le back
  recalcule → 129 km (BRouter a changé son graphe, ou tu es
  passé sur OSRM en fallback). Le client voit "127" mais est
  facturé "129" → réclamation.

  Solution : signer le résultat avec un token éphémère.
  - Back calcule 127 km → génère un token abc123 valable 15 min
   → stocke en Redis : abc123 → {distance: 127, waypoints:  
  [...]}
  - Renvoie au front : {distance: 127, token: "abc123"}
  - Le front POST /reserver avec le token
  - Le back lit Redis avec le token → utilise la distance
  mémorisée 
  - Si token expiré → recalcule ou demande au client de refaire

  ---
  3. 🚦 Rate-limiting & abus
  
  Avant : chaque client tape brouter.de avec sa propre IP. Si
  un client abuse, c'est son IP qui est bannie.
  Après : c'est ton serveur qui tape brouter.de pour tous. Un
  bot qui spam ton /api/itineraire → ton IP est bannie par
  brouter → toute ton app tombe.

  Solution :
  - Rate-limit par session/IP côté ton back (tu as déjà /quota
  amorcé dans web.py:64)
  - Cache agressif (même trajet ≤ 1 requête/jour)
  - Fallback en cascade : BRouter → OSRM → Haversine × 1.3

  ---
  4. 🗺️  Rendu de la carte (polyline)
  
  Aujourd'hui le JS reçoit le GeoJSON directement de brouter et
   Leaflet le dessine. Si ton back devient intermédiaire, il
  doit transmettre le GeoJSON complet au front (peut faire
  50-200 Ko selon la longueur du trajet).

  Solution : simple, tu renvoies juste le JSON tel quel. Pas de
   vrai défi, juste à ne pas oublier.

  ---
  5. 🔐 Validation des waypoints eux-mêmes

  Le client envoie maintenant des coordonnées GPS [lat, lon].
  Il peut envoyer n'importe quoi :
  - Coordonnées au milieu de l'océan
  - 500 waypoints pour faire crasher ton serveur
  - Un waypoint à New York et un à Tokyo (calcul énorme)

  Solution :
  - Limiter le nombre de waypoints (max 10 ?)

  - Bounding box Madagascar : rejeter si lat hors [-25.7,
  -11.9] ou lon hors [43.2, 50.5]
  - Timeout sur l'appel BRouter (5s max)

  ---
  Défis "non techniques" mais réels
  
  - Offline / mauvaise 3G : si le client a une connexion
  pourrie, aujourd'hui il peut encore utiliser Haversine en
  local. Avec le back, il ne peut plus rien faire sans
  connexion à ton serveur. Peu grave car il ne peut pas
  réserver hors ligne de toute façon.
  - Coût serveur : chaque calcul consomme du CPU/RAM de ton VPS
   (léger, mais ×1000 clients ça compte).
  - Dépendance renforcée à ton back : si ton FastAPI tombe,
  plus AUCUN calcul possible (avant, brouter.de restait
  accessible).

  ---
  Verdict

  C'est faisable et c'est la bonne approche. Les défis sont
  tous connus et résolus dans l'industrie (cache + token
  éphémère + rate-limit + validation waypoints).

  Ordre d'effort estimé :
  - MVP fonctionnel : ~1 journée de dev
  - Version robuste avec cache Redis + tokens : ~2-3 jours
  - Version production avec OSRM self-hosted en plus : ~1
  semaine
  
  Ma question pour toi avant de planifier : est-ce que tu vas
  facturer au km dans les prochains mois ? Si oui → on planifie
   maintenant. Si non avant 6 mois → on garde une note et on
  avance sur d'autres features (OAuth, Mobile Money) qui ont
  plus d'impact immédiat sur ton business.
