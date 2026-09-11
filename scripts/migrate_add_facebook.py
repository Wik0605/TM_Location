"""Migration: rend google_id nullable et ajoute facebook_id sur la table users.

SQLite ne supporte pas ALTER COLUMN DROP NOT NULL, on recree la table.
Idempotent : detecte si la migration a deja tourne.
"""
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tm_location.db"


def already_migrated(cur: sqlite3.Cursor) -> bool:
    cols = {row[1]: row for row in cur.execute("PRAGMA table_info(users)").fetchall()}
    return "facebook_id" in cols and cols["google_id"][3] == 0


def migrate() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"DB introuvable: {DB_PATH}")

    backup = DB_PATH.with_suffix(
        f".db.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    shutil.copy2(DB_PATH, backup)
    print(f"Backup cree: {backup.name}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if already_migrated(cur):
        print("Migration deja appliquee.")
        conn.close()
        return

    cur.executescript(
        """
        BEGIN;

        CREATE TABLE users_new (
            id INTEGER PRIMARY KEY,
            google_id VARCHAR(100) UNIQUE,
            facebook_id VARCHAR(100) UNIQUE,
            email VARCHAR(255) NOT NULL UNIQUE,
            name VARCHAR(150) NOT NULL,
            picture VARCHAR(500),
            created_at DATETIME NOT NULL
        );

        INSERT INTO users_new (id, google_id, email, name, picture, created_at)
        SELECT id, google_id, email, name, picture, created_at FROM users;

        DROP TABLE users;
        ALTER TABLE users_new RENAME TO users;

        CREATE INDEX ix_users_google_id ON users (google_id);
        CREATE INDEX ix_users_facebook_id ON users (facebook_id);

        COMMIT;
        """
    )
    conn.close()
    print("Migration OK: google_id nullable, facebook_id ajoute.")


if __name__ == "__main__":
    migrate()
