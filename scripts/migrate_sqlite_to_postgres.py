"""Migration one-shot SQLite -> PostgreSQL avec remapping int -> UUID v7.

Usage :
    python scripts/migrate_sqlite_to_postgres.py

Pré-requis :
- `tml-pg` démarré, migration Alembic appliquée (6 tables vides).
- `data/tm_location.db` présent (source).
- `DATABASE_URL` pointant sur PG dans `.env`.

Le script est idempotent uniquement sur une base PG VIDE. Il refuse de
tourner si une des tables cibles contient déjà des lignes.
"""
from __future__ import annotations

import asyncio
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.utils.ids import new_uuid7

SQLITE_PATH = Path(__file__).resolve().parent.parent / "data" / "tm_location.db"

# Ordre impératif : parents avant enfants (contrainte FK).
TABLES = [
    "voitures",
    "types_location",
    "voiture_images",
    "users",
    "locations",
    "analytics_events",
]

# Colonnes à caster explicitement : SQLite stocke bool en INTEGER
# et DATETIME en TEXT ; asyncpg exige les types Python natifs.
BOOL_COLS: dict[str, set[str]] = {
    "voitures": {"is_available"},
}
DATETIME_COLS: dict[str, set[str]] = {
    "voitures": {"created_at", "updated_at"},
    "users": {"created_at"},
    "locations": {"date_debut", "date_fin", "created_at", "updated_at"},
    "analytics_events": {"created_at"},
}


def _parse_dt(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace(" ", "T"))


# Colonnes qui référencent une autre table : (col, table_cible).
FK_MAP: dict[str, dict[str, str]] = {
    "types_location":   {"voiture_id": "voitures"},
    "voiture_images":   {"voiture_id": "voitures"},
    "locations":        {"voiture_id": "voitures",
                         "type_location_id": "types_location"},
    "analytics_events": {"voiture_id": "voitures",
                         "type_location_id": "types_location",
                         "location_id": "locations"},
}


def _pg_dsn() -> str:
    """Convertit l'URL asyncpg SQLAlchemy en DSN brut pour asyncpg.connect()."""
    url = settings.database_url
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def _ensure_target_empty(conn: asyncpg.Connection) -> None:
    for t in TABLES:
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {t}")
        if count:
            raise SystemExit(
                f"[STOP] Table '{t}' contient déjà {count} lignes. "
                "Script conçu pour une base PG vide."
            )


def _read_sqlite_table(cur: sqlite3.Cursor, table: str) -> list[dict]:
    cur.execute(f"SELECT * FROM {table}")
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


async def migrate() -> None:
    if not SQLITE_PATH.exists():
        raise SystemExit(f"[STOP] SQLite introuvable: {SQLITE_PATH}")

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    cur = sqlite_conn.cursor()

    pg = await asyncpg.connect(_pg_dsn())
    await _ensure_target_empty(pg)

    # Mapping global : table -> {ancien_id_int: nouveau_uuid}.
    id_maps: dict[str, dict[int, UUID]] = {t: {} for t in TABLES}

    total_inserted = 0

    for table in TABLES:
        rows = _read_sqlite_table(cur, table)
        if not rows:
            print(f"  {table}: 0 ligne, skip")
            continue

        fk_cols = FK_MAP.get(table, {})
        remapped: list[dict] = []
        for row in rows:
            new_row = dict(row)
            old_id = new_row.pop("id")
            new_uuid = new_uuid7()
            id_maps[table][old_id] = new_uuid
            new_row["id"] = new_uuid

            for col in BOOL_COLS.get(table, ()):
                if new_row.get(col) is not None:
                    new_row[col] = bool(new_row[col])

            for col in DATETIME_COLS.get(table, ()):
                new_row[col] = _parse_dt(new_row.get(col))

            for col, parent_table in fk_cols.items():
                old_fk = new_row.get(col)
                if old_fk is None:
                    continue
                new_fk = id_maps[parent_table].get(old_fk)
                if new_fk is None:
                    raise SystemExit(
                        f"[STOP] FK orpheline: {table}.{col}={old_fk} "
                        f"non trouvée dans {parent_table}"
                    )
                new_row[col] = new_fk

            remapped.append(new_row)

        cols = list(remapped[0].keys())
        placeholders = ", ".join(f"${i+1}" for i in range(len(cols)))
        sql = (
            f"INSERT INTO {table} ({', '.join(cols)}) "
            f"VALUES ({placeholders})"
        )
        values = [[r[c] for c in cols] for r in remapped]
        await pg.executemany(sql, values)
        total_inserted += len(remapped)
        print(f"  {table}: {len(remapped)} lignes insérées")

    await pg.close()
    sqlite_conn.close()
    print(f"\n[OK] {total_inserted} lignes migrées au total.")


if __name__ == "__main__":
    asyncio.run(migrate())
