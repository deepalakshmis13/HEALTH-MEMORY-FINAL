"""
One-off migration: copy an existing SQLite health-memory database into MongoDB.

The application no longer uses SQLite. This script exists so an installation
that already holds real data can move it across instead of discarding it.

    python migrate_sqlite_to_mongo.py                      # ./legacy_sqlite/health_memory.db
    python migrate_sqlite_to_mongo.py --sqlite /path/to.db
    python migrate_sqlite_to_mongo.py --drop-existing      # replace target data

It reads the old file with the standard library's ``sqlite3`` module only —
no SQLAlchemy, no application models on the read side — and writes through the
same MongoDB layer the application uses, so ids, types and counters end up
exactly as the running system expects.

Columns that no longer exist in the current document model are reported rather
than dropped quietly, so nothing is lost without you being told.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from config import BASE_DIR, MONGODB_DB_NAME
from database import get_database, init_db, sync_counter
from mongo_orm import _DateTime, _JSON, metadata

# Roles were renamed when the verification role became "Reviewer"; the old
# spelling is translated on the way in so migrated logins keep working.
ROLE_RENAMES = {"pharmacist": "reviewer"}
TABLE_RENAMES = {"pharmacists": "reviewers"}
FIELD_RENAMES = {
    "reviewers": {"pharmacy_name": "organisation_name"},
    "verification_results": {
        "pharmacist_id": "reviewer_id",
        "pharmacist_name": "reviewer_name",
    },
}
ROLE_FIELDS = {"role", "grantee_role", "author_role", "actor_role"}


def _coerce(model, field: str, value: Any) -> Any:
    """Turn a SQLite cell into the value the document model expects."""
    column = model.__columns__.get(field)
    if column is None or value is None:
        return value

    if isinstance(column.type, _JSON):
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value

    if isinstance(column.type, _DateTime):
        if isinstance(value, datetime):
            return value
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(str(value), fmt)
            except ValueError:
                continue
        return value

    return column.type.coerce(value)


def _sqlite_tables(connection: sqlite3.Connection) -> List[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return [row[0] for row in rows]


def migrate(sqlite_path: Path, drop_existing: bool = False) -> int:
    if not sqlite_path.exists():
        print(f"No SQLite database at {sqlite_path} — nothing to migrate.")
        return 1

    init_db()
    database = get_database()

    connection = sqlite3.connect(str(sqlite_path))
    connection.row_factory = sqlite3.Row

    source_tables = set(_sqlite_tables(connection))
    models_by_table = {model.__tablename__: model for model in metadata.models}

    total = 0
    skipped_fields: Dict[str, set] = {}

    for old_table in sorted(source_tables):
        new_table = TABLE_RENAMES.get(old_table, old_table)
        model = models_by_table.get(new_table)
        if model is None:
            print(f"  ! {old_table}: no matching collection in the current model — skipped")
            continue

        rows = connection.execute(f'SELECT * FROM "{old_table}"').fetchall()
        if not rows:
            print(f"  · {old_table}: empty")
            continue

        if drop_existing:
            database[new_table].delete_many({})

        renames = FIELD_RENAMES.get(new_table, {})
        documents: List[Dict[str, Any]] = []
        highest = 0

        for row in rows:
            document: Dict[str, Any] = {}
            for key in row.keys():
                field = renames.get(key, key)
                value = row[key]

                if field == "id":
                    document["_id"] = int(value)
                    highest = max(highest, int(value))
                    continue
                if field not in model.__columns__:
                    skipped_fields.setdefault(old_table, set()).add(key)
                    continue
                if field in ROLE_FIELDS and isinstance(value, str):
                    value = ROLE_RENAMES.get(value, value)
                document[field] = _coerce(model, field, value)

            # Fill in any field the old schema did not have.
            for name, column in model.__columns__.items():
                if column.primary_key or name in document:
                    continue
                document[name] = column.build_default()

            documents.append(document)

        if documents:
            database[new_table].insert_many(documents)
            sync_counter(new_table, highest)
            total += len(documents)
            label = f"{old_table} -> {new_table}" if old_table != new_table else old_table
            print(f"  ✓ {label}: {len(documents)} document(s)")

    connection.close()

    if skipped_fields:
        print("\nColumns present in SQLite but absent from the current document model:")
        for table, fields in sorted(skipped_fields.items()):
            print(f"  {table}: {', '.join(sorted(fields))}")
        print("Nothing above was written. Review it before deleting the SQLite file.")

    print(f"\nMigrated {total} document(s) into MongoDB database {MONGODB_DB_NAME!r}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sqlite",
        default=str(BASE_DIR / "legacy_sqlite" / "health_memory.db"),
        help="Path to the legacy SQLite database file.",
    )
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Clear each target collection before inserting.",
    )
    args = parser.parse_args()
    return migrate(Path(args.sqlite), drop_existing=args.drop_existing)


if __name__ == "__main__":
    sys.exit(main())
