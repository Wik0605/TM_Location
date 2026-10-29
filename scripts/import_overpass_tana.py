"""
Import fokontany et communes d'Antananarivo depuis Overpass API → table quartiers.
Usage : python scripts/import_overpass_tana.py
"""
import json
import os
import ssl
import sys
import urllib.request
import urllib.parse

import psycopg2
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
import shapely.wkt

DB_DSN = os.getenv(
    "DATABASE_URL",
    "host=localhost port=5432 dbname=tm_location user=postgres password=dev",
)

# Bounding box Antananarivo étendue (S,W,N,E pour Overpass)
BBOX = "-19.05,47.40,-18.70,47.70"

QUERY = f"""
[out:json][timeout:120];
(
  relation["boundary"="administrative"]["admin_level"="10"]({BBOX});
  relation["boundary"="administrative"]["admin_level"="11"]({BBOX});
  relation["boundary"="administrative"]["admin_level"="8"]({BBOX});
);
out geom;
"""


def fetch_overpass(query: str) -> dict:
    url = "https://overpass.kumi.systems/api/interpreter"
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("User-Agent", "TM_Location/1.0")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    print("Requête Overpass en cours...")
    with urllib.request.urlopen(req, timeout=130, context=ctx) as resp:
        return json.loads(resp.read())


def relation_to_multipolygon(element: dict):
    """Convertit une relation Overpass en MultiPolygon Shapely."""
    members = element.get("members", [])
    outer_ways = [m for m in members if m["type"] == "way" and m.get("role") == "outer"]
    inner_ways = [m for m in members if m["type"] == "way" and m.get("role") == "inner"]

    def way_to_coords(way):
        return [(n["lon"], n["lat"]) for n in way.get("geometry", [])]

    def build_ring(ways):
        if not ways:
            return []
        segments = [way_to_coords(w) for w in ways if way_to_coords(w)]
        if not segments:
            return []
        # Assemble les segments en anneaux fermés
        ring = list(segments[0])
        used = {0}
        for _ in range(len(segments) - 1):
            last = ring[-1]
            for i, seg in enumerate(segments):
                if i in used:
                    continue
                if seg[0] == last:
                    ring.extend(seg[1:])
                    used.add(i)
                    break
                elif seg[-1] == last:
                    ring.extend(reversed(seg[:-1]))
                    used.add(i)
                    break
        return ring

    try:
        from shapely.geometry import Polygon, MultiPolygon

        outer_ring = build_ring(outer_ways)
        inner_rings = [build_ring([w]) for w in inner_ways]
        inner_rings = [r for r in inner_rings if len(r) >= 3]

        if len(outer_ring) < 3:
            return None

        poly = Polygon(outer_ring, inner_rings)
        if not poly.is_valid:
            poly = poly.buffer(0)
        return MultiPolygon([poly]) if poly.geom_type == "Polygon" else poly
    except Exception as e:
        print(f"  Erreur géométrie osm_id={element.get('id')}: {e}", file=sys.stderr)
        return None


def main():
    result = fetch_overpass(QUERY)
    elements = result.get("elements", [])
    print(f"{len(elements)} relations récupérées.")

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    inserted = 0
    skipped = 0

    for el in elements:
        tags = el.get("tags", {})
        nom = tags.get("name", "").strip()
        if not nom:
            skipped += 1
            continue

        level = tags.get("admin_level", "")
        if level in ("10", "11"):
            type_ = "fokontany"
        elif level == "8":
            type_ = "commune"
        else:
            skipped += 1
            continue

        nom_court = tags.get("short_name") or tags.get("name:mg") or nom
        osm_id = el.get("id")

        geom = relation_to_multipolygon(el)
        if geom is None or geom.is_empty:
            skipped += 1
            continue

        wkt = shapely.wkt.dumps(geom)

        cur.execute(
            """
            INSERT INTO quartiers (nom, nom_court, type, actif, osm_id, geom)
            VALUES (%s, %s, %s, true, %s, ST_Multi(ST_GeomFromText(%s, 4326)))
            ON CONFLICT (osm_id) DO UPDATE
              SET nom       = EXCLUDED.nom,
                  nom_court = EXCLUDED.nom_court,
                  type      = EXCLUDED.type,
                  geom      = EXCLUDED.geom
            """,
            (nom, nom_court, type_, osm_id, wkt),
        )
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"Importé : {inserted} | Ignoré : {skipped}")


if __name__ == "__main__":
    main()
