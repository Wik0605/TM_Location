"""
Import fokontany d'Antananarivo depuis GeoBoundaries ADM4 shapefile → table quartiers.
Usage : python scripts/import_geoboundaries_tana.py
"""
import os
import sys

import psycopg2
import shapefile
from shapely.geometry import shape, MultiPolygon, Polygon
import shapely.wkt

DB_DSN = os.getenv(
    "DATABASE_URL",
    "host=localhost port=5432 dbname=tm_location user=postgres password=dev",
)

SHP_PATH = "/tmp/MDG_ADM4/MDG_ADM4.shp"

# Bbox Antananarivo (lon_min, lon_max, lat_min, lat_max)
MIN_LON, MAX_LON = 47.40, 47.70
MIN_LAT, MAX_LAT = -19.05, -18.70


def to_multipolygon(geom):
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    if geom.geom_type == "MultiPolygon":
        return geom
    return None


def main():
    r = shapefile.Reader(SHP_PATH)
    fields = [f[0] for f in r.fields[1:]]
    print(f"Colonnes : {fields}")

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    inserted = 0
    skipped = 0

    for sr in r.shapeRecords():
        bbox = sr.shape.bbox
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2

        if not (MIN_LON <= cx <= MAX_LON and MIN_LAT <= cy <= MAX_LAT):
            continue

        rec = dict(zip(fields, sr.record))
        nom = (rec.get("Name") or "").strip()
        if not nom:
            skipped += 1
            continue

        try:
            geom = shape(sr.shape.__geo_interface__)
            mp = to_multipolygon(geom)
            if mp is None or mp.is_empty:
                skipped += 1
                continue
            if not mp.is_valid:
                mp = mp.buffer(0)
                mp = to_multipolygon(mp)
        except Exception as e:
            print(f"  Erreur géométrie {nom}: {e}", file=sys.stderr)
            skipped += 1
            continue

        wkt = shapely.wkt.dumps(mp)
        feature_id = rec.get("feature_id") or rec.get("gbid") or None

        cur.execute(
            """
            INSERT INTO quartiers (nom, nom_court, type, actif, geom)
            VALUES (%s, %s, 'fokontany', true, ST_Multi(ST_GeomFromText(%s, 4326)))
            """,
            (nom, nom, wkt),
        )
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"Importé : {inserted} fokontany | Ignoré : {skipped}")


if __name__ == "__main__":
    main()
