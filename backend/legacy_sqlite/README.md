# Legacy SQLite database

The application no longer reads this file — it runs entirely on MongoDB.
It is kept only so an existing installation can carry its data across:

```bash
cd backend
python migrate_sqlite_to_mongo.py            # reads ./legacy_sqlite/health_memory.db
python migrate_sqlite_to_mongo.py --sqlite /path/to/your.db --drop-existing
```

The script reports any column it could not map instead of dropping it silently.
Once you have verified the migrated data in MongoDB, this folder can be deleted.
