"""MongoDB client, session and query layer for the health-memory store.

The application previously ran on SQLAlchemy + SQLite. It now runs entirely on
MongoDB: this module owns the connection (driven by ``MONGODB_URI``), hands out
per-request sessions, and implements the query vocabulary the services use.
Neither SQLAlchemy nor sqlite3 is imported anywhere in the backend.

Identifiers stay integers. Each collection's ``_id`` is an integer allocated by
an atomic ``$inc`` against a ``_counters`` document, so every route, schema and
front-end call that passes a numeric id keeps working unchanged.

A note on transactions: MongoDB only offers multi-document transactions on a
replica set, and the application never needed them — each request writes a
small set of related documents and reports failures to the caller. ``flush()``
therefore performs the writes and ``commit()`` is a flush; this matches the
observable behaviour of the previous layer for every call site in the codebase.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

from config import (
    MONGODB_DB_NAME,
    MONGODB_FALLBACK_ENABLED,
    MONGODB_LOCAL_PATH,
    MONGODB_TIMEOUT_MS,
    MONGODB_URI,
)
from mongo_orm import (
    BoundColumn,
    Criterion,
    ModelBase,
    Order,
    document_base,
    metadata,
)

logger = logging.getLogger("health_memory.database")

Base = document_base()

COUNTER_COLLECTION = "_counters"


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------
_client = None
_database = None
_using_in_memory = False
_fallback_kind = ""
# The file-backed development store keeps a SQLite handle per client and SQLite
# refuses cross-thread use, while the server answers requests on a thread pool.
# Each thread therefore gets its own client onto the same files.
_thread_local = threading.local()


def _connect():
    """Open the MongoDB connection described by MONGODB_URI.

    If the server cannot be reached and MONGODB_IN_MEMORY_FALLBACK is enabled
    (the default for local development), an in-process MongoDB-compatible
    store is used instead so the application still starts. The fallback is
    logged loudly and is never silent.
    """
    global _client, _database, _using_in_memory

    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=MONGODB_TIMEOUT_MS)
        client.admin.command("ping")
        _client = client
        _database = client[MONGODB_DB_NAME]
        _using_in_memory = False
        logger.info("Connected to MongoDB database %r", MONGODB_DB_NAME)
        return _database
    except (ServerSelectionTimeoutError, PyMongoError) as exc:
        if not MONGODB_FALLBACK_ENABLED:
            raise RuntimeError(
                "Could not reach MongoDB at MONGODB_URI. Set MONGODB_URI to a "
                "running MongoDB instance, or set MONGODB_LOCAL_FALLBACK=1 to "
                "run against an in-process store for development."
            ) from exc

        logger.warning(
            "MongoDB at MONGODB_URI is unreachable (%s). Falling back to a "
            "local development store. Set MONGODB_URI to a real deployment "
            "for anything beyond local development.",
            exc.__class__.__name__,
        )
        _client, _database = _local_fallback()
        _using_in_memory = True
        return _database


def _local_fallback():
    """A MongoDB-compatible store for machines without a MongoDB server.

    Preferred: a file-backed store under MONGODB_LOCAL_PATH, so seeded demo
    data survives a restart exactly as a real deployment would. If that package
    is unavailable, an in-memory store is used and data is lost on restart.
    Neither path is for production — both exist only so `uvicorn main:app`
    works on a fresh checkout.
    """
    global _fallback_kind
    try:
        from montydb import MontyClient, set_storage

        MONGODB_LOCAL_PATH.mkdir(parents=True, exist_ok=True)
        set_storage(str(MONGODB_LOCAL_PATH), storage="sqlite")
        client = MontyClient(str(MONGODB_LOCAL_PATH))
        _fallback_kind = "file"
        logger.warning(
            "Using the file-backed development store at %s.", MONGODB_LOCAL_PATH
        )
        return client, client[MONGODB_DB_NAME]
    except ImportError:
        pass

    try:
        import mongomock
    except ImportError:  # pragma: no cover - both packages are declared
        raise RuntimeError(
            "MongoDB is unreachable and no local fallback package is installed. "
            "Install 'montydb' or 'mongomock', or point MONGODB_URI at a "
            "running MongoDB instance."
        )

    _fallback_kind = "memory"
    logger.warning(
        "Using an IN-MEMORY store. This store belongs to THIS PROCESS ONLY: data "
        "seeded by 'python seed.py' in a separate process will NOT be visible to "
        "the server, and nothing survives a restart. Install 'montydb' for a "
        "file-backed development store, or set MONGODB_URI to a real server."
    )
    client = mongomock.MongoClient()
    return client, client[MONGODB_DB_NAME]


def get_database():
    """Return the database handle for the calling thread."""
    if _database is None:
        _connect()
    if _fallback_kind != "file":
        return _database

    handle = getattr(_thread_local, "database", None)
    if handle is None:
        from montydb import MontyClient

        handle = MontyClient(str(MONGODB_LOCAL_PATH))[MONGODB_DB_NAME]
        _thread_local.database = handle
    return handle


def using_in_memory_store() -> bool:
    """True when either local development fallback is active."""
    if _database is None:
        get_database()
    return _using_in_memory


def store_description() -> Dict[str, Any]:
    """What the application is actually talking to, in plain terms.

    Reported by /api/health and printed at startup, because an empty database
    and a misconfigured one look identical from the interface — the caregiver
    simply sees no patients — and the operator deserves to be told which it is.
    """
    if _database is None:
        get_database()
    if not _using_in_memory:
        kind, persistent, detail = "mongodb", True, f"{MONGODB_URI} / {MONGODB_DB_NAME}"
    elif _fallback_kind == "file":
        kind, persistent, detail = (
            "local-file-store", True, str(MONGODB_LOCAL_PATH),
        )
    else:
        kind, persistent, detail = (
            "in-memory", False,
            "process-local; seed in the same process and expect no persistence",
        )
    return {"store": kind, "persistent": persistent, "detail": detail}


def store_counts() -> Dict[str, int]:
    """Row counts for the collections that decide whether a demo works."""
    database = get_database()
    return {
        name: database[name].count_documents({})
        for name in ("users", "patients", "doctors", "caregivers", "reviewers",
                     "care_assignments", "memory_events", "documents")
    }


def is_seeded() -> bool:
    """A database with no users cannot log anybody in."""
    return get_database()["users"].count_documents({}) > 0


def next_id(collection_name: str) -> int:
    """Allocate the next integer id for a collection, atomically."""
    database = get_database()
    doc = database[COUNTER_COLLECTION].find_one_and_update(
        {"_id": collection_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    if doc is None:  # mongomock without return_document support
        doc = database[COUNTER_COLLECTION].find_one({"_id": collection_name})
    return int(doc["seq"])


def sync_counter(collection_name: str, highest_id: int) -> None:
    """Make sure the counter never re-issues an id that already exists."""
    database = get_database()
    current = database[COUNTER_COLLECTION].find_one({"_id": collection_name})
    if current is None or int(current.get("seq", 0)) < highest_id:
        database[COUNTER_COLLECTION].update_one(
            {"_id": collection_name},
            {"$set": {"seq": int(highest_id)}},
            upsert=True,
        )


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------
def _merge(clauses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Combine filter fragments, keeping both when they touch the same key."""
    merged: Dict[str, Any] = {}
    extra: List[Dict[str, Any]] = []
    for clause in clauses:
        for key, value in clause.items():
            if key in merged and merged[key] != value:
                extra.append({key: value})
            else:
                merged[key] = value
    if extra:
        conditions = [merged] if merged else []
        conditions.extend(extra)
        return {"$and": conditions}
    return merged


class Query:
    """The subset of the previous query API the application actually uses."""

    def __init__(self, session: "Session", model):
        self.session = session
        self.model = model
        self._clauses: List[Dict[str, Any]] = []
        self._sort: List[Tuple[str, int]] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None

    # -- builders -----------------------------------------------------------
    def _clone(self) -> "Query":
        clone = Query(self.session, self.model)
        clone._clauses = list(self._clauses)
        clone._sort = list(self._sort)
        clone._limit = self._limit
        clone._offset = self._offset
        return clone

    def filter(self, *criteria) -> "Query":
        clone = self._clone()
        for criterion in criteria:
            if criterion is None:
                continue
            if isinstance(criterion, Criterion):
                clone._clauses.append(criterion.clause)
            elif isinstance(criterion, dict):
                clone._clauses.append(criterion)
            else:
                raise TypeError(f"Unsupported filter expression: {criterion!r}")
        return clone

    def filter_by(self, **kwargs) -> "Query":
        columns = self.model.__columns__
        clause = {}
        for name, value in kwargs.items():
            column = columns[name]
            clause["_id" if column.primary_key else name] = column.type.coerce(value)
        clone = self._clone()
        clone._clauses.append(clause)
        return clone

    def order_by(self, *specs) -> "Query":
        clone = self._clone()
        for spec in specs:
            if spec is None:
                continue
            if isinstance(spec, Order):
                clone._sort.append((spec.field, ASCENDING if spec.direction > 0 else DESCENDING))
            elif isinstance(spec, BoundColumn):
                clone._sort.append((spec.key, ASCENDING))
            else:
                raise TypeError(f"Unsupported ordering expression: {spec!r}")
        return clone

    def limit(self, value: int) -> "Query":
        clone = self._clone()
        clone._limit = value
        return clone

    def offset(self, value: int) -> "Query":
        clone = self._clone()
        clone._offset = value
        return clone

    # -- execution ----------------------------------------------------------
    @property
    def _collection(self):
        return get_database()[self.model.__tablename__]

    def _mongo_filter(self) -> Dict[str, Any]:
        return _merge(self._clauses) if self._clauses else {}

    def _cursor(self):
        cursor = self._collection.find(self._mongo_filter())
        if self._sort:
            cursor = cursor.sort(self._sort)
        if self._offset:
            cursor = cursor.skip(self._offset)
        if self._limit is not None:
            cursor = cursor.limit(self._limit)
        return cursor

    def all(self) -> List[Any]:
        return [self.session._materialise(self.model, doc) for doc in self._cursor()]

    def first(self):
        for doc in self._cursor().limit(1):
            return self.session._materialise(self.model, doc)
        return None

    def one_or_none(self):
        found = self.limit(2).all()
        if not found:
            return None
        if len(found) > 1:
            raise RuntimeError(
                f"Expected at most one {self.model.__name__}, found several."
            )
        return found[0]

    def get(self, identifier):
        return self.filter(
            BoundColumn(self.model, self.model.__columns__["id"]) == identifier
        ).first()

    def count(self) -> int:
        return self._collection.count_documents(self._mongo_filter())

    def delete(self, **_ignored) -> int:
        targets = self.all()
        for obj in targets:
            self.session.delete(obj)
        self.session.flush()
        return len(targets)

    def exists(self) -> bool:
        return self.first() is not None

    def __iter__(self):
        return iter(self.all())


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------
class Session:
    """One unit of work. Created per request by :func:`get_db`."""

    def __init__(self):
        self._identity: Dict[Tuple[str, Any], ModelBase] = {}
        self._new: List[ModelBase] = []
        self._deleted: List[ModelBase] = []

    # -- querying -----------------------------------------------------------
    def query(self, model) -> Query:
        return Query(self, model)

    def get(self, model, identifier):
        return self.query(model).get(identifier)

    def _materialise(self, model, doc: Dict[str, Any]):
        """Return the session-local instance for a document."""
        key = (model.__tablename__, doc.get("_id"))
        existing = self._identity.get(key)
        if existing is not None and not existing._deleted:
            return existing
        obj = model.from_document(doc, session=self)
        self._identity[key] = obj
        return obj

    # -- unit of work -------------------------------------------------------
    def add(self, obj: ModelBase) -> None:
        if obj not in self._new:
            object.__setattr__(obj, "_session", self)
            self._new.append(obj)

    def add_all(self, objs: Iterable[ModelBase]) -> None:
        for obj in objs:
            self.add(obj)

    def delete(self, obj: ModelBase) -> None:
        if obj in self._new:
            self._new.remove(obj)
            return
        if obj not in self._deleted:
            self._deleted.append(obj)

    def flush(self) -> None:
        """Write pending inserts, updates and deletes to MongoDB."""
        database = get_database()

        # Inserts first, so callers can read back freshly-allocated ids.
        pending, self._new = self._new, []
        for obj in pending:
            model = type(obj)
            if obj._data.get("id") is None:
                obj._data["id"] = next_id(model.__tablename__)
            database[model.__tablename__].insert_one(obj.to_document())
            obj._take_snapshot()
            object.__setattr__(obj, "_session", self)
            self._identity[(model.__tablename__, obj._data["id"])] = obj

        # Updates for anything loaded through this session that changed.
        for (table, identifier), obj in list(self._identity.items()):
            if obj._deleted or obj in self._deleted:
                continue
            changed = obj._changed_fields()
            changed.pop("id", None)
            if changed:
                database[table].update_one({"_id": identifier}, {"$set": changed})
                obj._take_snapshot()

        # Deletes, including declared cascades.
        pending_deletes, self._deleted = self._deleted, []
        for obj in pending_deletes:
            self._cascade_delete(obj, database)

    def _cascade_delete(self, obj: ModelBase, database) -> None:
        model = type(obj)
        identifier = obj._data.get("id")
        if identifier is None:
            return
        for rel in model.__relationships__.values():
            if not rel.deletes_orphans:
                continue
            rel._resolve()
            if rel.direction != "one_to_many":
                continue
            target = rel.target
            children = (
                self.query(target)
                .filter(BoundColumn(target, target.__columns__[rel.remote_key]) == identifier)
                .all()
            )
            for child in children:
                self._cascade_delete(child, database)
        database[model.__tablename__].delete_one({"_id": identifier})
        object.__setattr__(obj, "_deleted", True)
        self._identity.pop((model.__tablename__, identifier), None)

    def commit(self) -> None:
        self.flush()

    def rollback(self) -> None:
        """Discard work that has not been flushed yet.

        MongoDB writes performed by an earlier ``flush()`` in the same request
        are already durable and cannot be undone here; no call site in this
        application depends on undoing them.
        """
        self._new.clear()
        self._deleted.clear()
        for obj in self._identity.values():
            if obj._snapshot is not None:
                object.__setattr__(obj, "_data", dict(obj._snapshot))

    def refresh(self, obj: ModelBase) -> ModelBase:
        model = type(obj)
        identifier = obj._data.get("id")
        if identifier is None:
            return obj
        doc = get_database()[model.__tablename__].find_one({"_id": identifier})
        if doc is None:
            return obj
        for attr, column in model.__columns__.items():
            obj._data[attr] = doc.get("_id") if column.primary_key else doc.get(attr)
        obj._take_snapshot()
        return obj

    def expunge_all(self) -> None:
        self._identity.clear()
        self._new.clear()
        self._deleted.clear()

    def close(self) -> None:
        self.expunge_all()

    # -- context manager ----------------------------------------------------
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()
        return False


def SessionLocal() -> Session:  # noqa: N802 — kept as a call-site-compatible name
    """Create a new session (mirrors the previous session factory)."""
    return Session()


def get_db():
    """FastAPI dependency — one session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------
def init_db() -> None:
    """Connect and create the declared indexes."""
    import models  # noqa: F401  (registers the document classes)

    database = get_database()
    metadata.create_all(database)
    _realign_counters(database)


def _realign_counters(database) -> None:
    """Point every id counter past the highest id already stored."""
    for model in metadata.models:
        top = list(
            database[model.__tablename__].find({}, {"_id": 1}).sort([("_id", DESCENDING)]).limit(1)
        )
        if top:
            highest = top[0].get("_id")
            if isinstance(highest, int):
                sync_counter(model.__tablename__, highest)


def drop_all() -> None:
    """Remove every application collection. Used by the seeding script."""
    import models  # noqa: F401

    database = get_database()
    for model in metadata.models:
        database[model.__tablename__].drop()
    database[COUNTER_COLLECTION].drop()


__all__ = [
    "Base",
    "is_seeded",
    "store_counts",
    "store_description",
    "Query",
    "Session",
    "SessionLocal",
    "drop_all",
    "get_database",
    "get_db",
    "init_db",
    "next_id",
    "sync_counter",
    "using_in_memory_store",
]
