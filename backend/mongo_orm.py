"""
Lightweight MongoDB document mapper for the health-memory store.

Why this module exists
----------------------
The application was originally written against SQLAlchemy + SQLite. The data
layer has now been migrated to MongoDB. Rather than scattering raw PyMongo
calls through ~24 service, route and agent modules (which would have meant
rewriting clinical logic that is already tested and correct), the migration
replaces the *mapper* underneath them: models keep declaring fields, and the
session keeps exposing the small query vocabulary the application actually
uses (`filter`, `order_by`, `limit`, `all`, `first`, `count`, `delete`).

Everything here talks to MongoDB and nothing here imports SQLAlchemy or
sqlite3. Documents are stored one collection per model, keyed by an integer
`_id` handed out by an atomic counter collection, so every existing integer
identifier in the API surface (``/api/patients/3``) keeps working.

Public surface used by the application:

    Column, ForeignKey, relationship
    Integer, String, Text, Boolean, DateTime, Float, JSON
    document_base, metadata
"""

from __future__ import annotations

import copy
import re
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional


# ---------------------------------------------------------------------------
# Column types
#
# These exist so `models.py` can keep documenting the shape and width of each
# field. MongoDB is schemaless, so the widths are advisory: they are used for
# the light coercion below and as living documentation of the data model.
# ---------------------------------------------------------------------------
class _Type:
    python_type: Any = None

    def __init__(self, length: Optional[int] = None):
        self.length = length

    def __call__(self, length: Optional[int] = None):
        return type(self)(length)

    def coerce(self, value):
        return value

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"{type(self).__name__}({self.length or ''})"


class _Integer(_Type):
    def coerce(self, value):
        if value is None or isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value
        try:
            return int(value)
        except (TypeError, ValueError):
            return value


class _Float(_Type):
    def coerce(self, value):
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return value


class _String(_Type):
    def coerce(self, value):
        if value is None or isinstance(value, str):
            return value
        return str(value)


class _Text(_String):
    pass


class _Boolean(_Type):
    def coerce(self, value):
        if value is None or isinstance(value, bool):
            return value
        return bool(value)


class _DateTime(_Type):
    def coerce(self, value):
        if value is None or isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime(value.year, value.month, value.day)
        return value


class _JSON(_Type):
    pass


# Instances, so `Column(Integer)` and `Column(String(160))` both work.
Integer = _Integer()
Float = _Float()
String = _String()
Text = _Text()
Boolean = _Boolean()
DateTime = _DateTime()
JSON = _JSON()


class ForeignKey:
    """Declares that a column points at ``"<collection>.<field>"``."""

    def __init__(self, target: str, **_ignored):
        self.target = target
        self.table, _, self.column = target.partition(".")


# ---------------------------------------------------------------------------
# Query expressions
# ---------------------------------------------------------------------------
class Criterion:
    """A MongoDB filter fragment produced by comparing a column."""

    def __init__(self, clause: Dict[str, Any]):
        self.clause = clause

    def __and__(self, other: "Criterion") -> "Criterion":
        return Criterion({"$and": [self.clause, other.clause]})

    def __or__(self, other: "Criterion") -> "Criterion":
        return Criterion({"$or": [self.clause, other.clause]})

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"Criterion({self.clause!r})"


def and_(*criteria: Criterion) -> Criterion:
    clauses = [c.clause for c in criteria if c is not None]
    if not clauses:
        return Criterion({})
    if len(clauses) == 1:
        return Criterion(clauses[0])
    return Criterion({"$and": clauses})


def or_(*criteria: Criterion) -> Criterion:
    clauses = [c.clause for c in criteria if c is not None]
    if not clauses:
        return Criterion({})
    if len(clauses) == 1:
        return Criterion(clauses[0])
    return Criterion({"$or": clauses})


def not_(criterion: Criterion) -> Criterion:
    return Criterion({"$nor": [criterion.clause]})


class Order:
    """A sort instruction: ``(field, direction)``."""

    def __init__(self, field: str, direction: int = 1):
        self.field = field
        self.direction = direction

    def as_tuple(self):
        return (self.field, self.direction)


def _escape(value: str) -> str:
    return re.escape(value)


class BoundColumn:
    """Class-level view of a column — the thing filters are built from."""

    __slots__ = ("model", "column")

    def __init__(self, model, column: "Column"):
        self.model = model
        self.column = column

    # -- identity -----------------------------------------------------------
    @property
    def key(self) -> str:
        """Storage key: the primary key lives in Mongo's ``_id``."""
        return "_id" if self.column.primary_key else self.column.name

    @property
    def name(self) -> str:
        return self.column.name

    # -- comparisons --------------------------------------------------------
    def __eq__(self, other):  # type: ignore[override]
        return Criterion({self.key: self._prep(other)})

    def __ne__(self, other):  # type: ignore[override]
        return Criterion({self.key: {"$ne": self._prep(other)}})

    def __lt__(self, other):
        return Criterion({self.key: {"$lt": self._prep(other)}})

    def __le__(self, other):
        return Criterion({self.key: {"$lte": self._prep(other)}})

    def __gt__(self, other):
        return Criterion({self.key: {"$gt": self._prep(other)}})

    def __ge__(self, other):
        return Criterion({self.key: {"$gte": self._prep(other)}})

    def in_(self, values: Iterable):
        return Criterion({self.key: {"$in": [self._prep(v) for v in values]}})

    def notin_(self, values: Iterable):
        return Criterion({self.key: {"$nin": [self._prep(v) for v in values]}})

    def is_(self, value):
        if value is None:
            return Criterion({self.key: None})
        return Criterion({self.key: self._prep(value)})

    def isnot(self, value):
        if value is None:
            return Criterion({self.key: {"$ne": None}})
        return Criterion({self.key: {"$ne": self._prep(value)}})

    isnot_ = isnot
    is_not = isnot

    def like(self, pattern: str):
        return Criterion({self.key: {"$regex": _sql_like_to_regex(pattern)}})

    def ilike(self, pattern: str):
        return Criterion(
            {self.key: {"$regex": _sql_like_to_regex(pattern), "$options": "i"}}
        )

    def contains(self, value: str):
        return Criterion({self.key: {"$regex": _escape(value), "$options": "i"}})

    def between(self, low, high):
        return Criterion({self.key: {"$gte": self._prep(low), "$lte": self._prep(high)}})

    # -- ordering -----------------------------------------------------------
    def desc(self) -> Order:
        return Order(self.key, -1)

    def asc(self) -> Order:
        return Order(self.key, 1)

    def _prep(self, value):
        return self.column.type.coerce(value)

    def __hash__(self):
        return hash((self.model.__name__, self.key))

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"<{self.model.__name__}.{self.column.name}>"


def _sql_like_to_regex(pattern: str) -> str:
    """Translate a SQL LIKE pattern into an anchored regular expression."""
    out = ["^"]
    for ch in pattern:
        if ch == "%":
            out.append(".*")
        elif ch == "_":
            out.append(".")
        else:
            out.append(re.escape(ch))
    out.append("$")
    return "".join(out)


# ---------------------------------------------------------------------------
# Column / relationship descriptors
# ---------------------------------------------------------------------------
_MISSING = object()


class Column:
    def __init__(
        self,
        type_=None,
        foreign_key: Optional[ForeignKey] = None,
        *,
        primary_key: bool = False,
        nullable: bool = True,
        default=_MISSING,
        index: bool = False,
        unique: bool = False,
        **_ignored,
    ):
        # `Column(Integer, ForeignKey("users.id"), nullable=False)` — the
        # foreign key arrives positionally, exactly as it did before.
        if isinstance(type_, ForeignKey):
            type_, foreign_key = String, type_
        self.type = type_ if type_ is not None else String
        self.foreign_key = foreign_key
        self.primary_key = primary_key
        self.nullable = nullable
        self.default = default
        self.index = index
        self.unique = unique
        self.name: str = ""
        self.model = None

    # -- storage ------------------------------------------------------------
    @property
    def key(self) -> str:
        return "_id" if self.primary_key else self.name

    def build_default(self):
        if self.default is _MISSING:
            return None
        if callable(self.default):
            return self.default()
        return self.default

    # -- descriptor ---------------------------------------------------------
    def __get__(self, obj, owner=None):
        if obj is None:
            return BoundColumn(owner, self)
        return obj._data.get(self.name)

    def __set__(self, obj, value):
        obj._data[self.name] = self.type.coerce(value)

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"Column({self.name!r})"


class relationship:  # noqa: N801 — mirrors the previous declaration style
    """A lazily-resolved link between two documents.

    Direction is inferred the same way the previous mapping declared it:
    if this model carries exactly one foreign key pointing at the target
    collection, the link is many-to-one; otherwise it is the reverse side and
    is resolved from the target's foreign key back to this collection.
    """

    def __init__(
        self,
        target: str,
        *,
        back_populates: Optional[str] = None,
        foreign_keys=None,
        uselist: Optional[bool] = None,
        cascade: str = "",
        **_ignored,
    ):
        self.target_name = target
        self.back_populates = back_populates
        self.declared_fk = foreign_keys
        self.uselist = uselist
        self.cascade = cascade or ""
        self.name: str = ""
        self.model = None
        self._resolved = False
        # filled in by _resolve()
        self.direction = ""      # "many_to_one" | "one_to_many"
        self.local_key = ""
        self.remote_key = ""

    # -- resolution ---------------------------------------------------------
    @property
    def target(self):
        return _REGISTRY[self.target_name]

    def _resolve(self):
        if self._resolved:
            return
        target = self.target
        local_fk = None

        if self.declared_fk:
            declared = self.declared_fk
            if not isinstance(declared, (list, tuple)):
                declared = [declared]
            first = declared[0]
            local_fk = first.name if isinstance(first, Column) else str(first)
        else:
            candidates = [
                col.name
                for col in self.model.__columns__.values()
                if col.foreign_key and col.foreign_key.table == target.__tablename__
            ]
            if len(candidates) == 1:
                local_fk = candidates[0]

        if local_fk:
            self.direction = "many_to_one"
            self.local_key = local_fk
            self.remote_key = "_id"
            if self.uselist is None:
                self.uselist = False
        else:
            remote = [
                col.name
                for col in target.__columns__.values()
                if col.foreign_key and col.foreign_key.table == self.model.__tablename__
            ]
            if not remote:
                raise RuntimeError(
                    f"Cannot resolve relationship {self.model.__name__}.{self.name} "
                    f"-> {self.target_name}: no foreign key found on either side."
                )
            self.direction = "one_to_many"
            self.local_key = "id"
            self.remote_key = remote[0]
            if self.uselist is None:
                self.uselist = True

        self._resolved = True

    @property
    def deletes_orphans(self) -> bool:
        return "delete-orphan" in self.cascade or "delete" in self.cascade

    # -- descriptor ---------------------------------------------------------
    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        self._resolve()
        session = obj._session
        if session is None:
            # Detached object: nothing to resolve against.
            return [] if self.uselist else None

        target = self.target
        if self.direction == "many_to_one":
            fk_value = obj._data.get(self.local_key)
            if fk_value is None:
                return None
            return session.query(target).filter(
                BoundColumn(target, target.__columns__["id"]) == fk_value
            ).first()

        own_id = obj._data.get("id")
        if own_id is None:
            return [] if self.uselist else None
        remote_col = target.__columns__[self.remote_key]
        query = session.query(target).filter(BoundColumn(target, remote_col) == own_id)
        return query.all() if self.uselist else query.first()

    def __set__(self, obj, value):
        self._resolve()
        if self.direction != "many_to_one":
            raise AttributeError(
                f"{self.model.__name__}.{self.name} is a collection and cannot be "
                "assigned directly; set the foreign key on the child instead."
            )
        obj._data[self.local_key] = None if value is None else value.id


# ---------------------------------------------------------------------------
# Model base
# ---------------------------------------------------------------------------
_REGISTRY: Dict[str, type] = {}
_TABLES: Dict[str, type] = {}


class _Metadata:
    """Stand-in for the old ``Base.metadata`` with a Mongo-shaped meaning."""

    @property
    def models(self) -> List[type]:
        return list(_TABLES.values())

    def create_all(self, database=None, **_ignored):
        """Create the declared indexes. Collections appear on first write."""
        if database is None:
            return
        for model in _TABLES.values():
            model.ensure_indexes(database)


metadata = _Metadata()


class ModelMeta(type):
    def __new__(mcls, name, bases, namespace):
        columns: Dict[str, Column] = {}
        relationships: Dict[str, relationship] = {}

        for base in bases:
            columns.update(getattr(base, "__columns__", {}) or {})
            relationships.update(getattr(base, "__relationships__", {}) or {})

        for attr, value in list(namespace.items()):
            if isinstance(value, Column):
                value.name = attr
                columns[attr] = value
            elif isinstance(value, relationship):
                value.name = attr
                relationships[attr] = value

        cls = super().__new__(mcls, name, bases, namespace)
        cls.__columns__ = columns
        cls.__relationships__ = relationships

        for col in columns.values():
            col.model = cls
        for rel in relationships.values():
            rel.model = cls

        if namespace.get("__tablename__"):
            _REGISTRY[name] = cls
            _TABLES[namespace["__tablename__"]] = cls
        return cls


class ModelBase(metaclass=ModelMeta):
    """Base document. Subclasses declare `__tablename__` and `Column`s."""

    __tablename__: str = ""
    __columns__: Dict[str, Column] = {}
    __relationships__: Dict[str, relationship] = {}

    metadata = metadata

    def __init__(self, **kwargs):
        object.__setattr__(self, "_data", {})
        object.__setattr__(self, "_session", None)
        object.__setattr__(self, "_snapshot", None)
        object.__setattr__(self, "_deleted", False)

        for attr, col in self.__columns__.items():
            self._data[attr] = col.build_default()

        for attr, value in kwargs.items():
            if attr in self.__columns__:
                self._data[attr] = self.__columns__[attr].type.coerce(value)
            elif attr in self.__relationships__:
                setattr(self, attr, value)
            else:
                raise TypeError(
                    f"{type(self).__name__}() got an unexpected field {attr!r}"
                )

    # -- (de)serialisation --------------------------------------------------
    def to_document(self) -> Dict[str, Any]:
        doc: Dict[str, Any] = {}
        for attr, col in self.__columns__.items():
            value = self._data.get(attr)
            if col.primary_key:
                if value is not None:
                    doc["_id"] = value
                continue
            doc[attr] = value
        return doc

    @classmethod
    def from_document(cls, doc: Dict[str, Any], session=None):
        obj = cls.__new__(cls)
        object.__setattr__(obj, "_data", {})
        object.__setattr__(obj, "_session", session)
        object.__setattr__(obj, "_deleted", False)
        for attr, col in cls.__columns__.items():
            if col.primary_key:
                obj._data[attr] = doc.get("_id")
            else:
                obj._data[attr] = doc.get(attr, col.build_default())
        object.__setattr__(obj, "_snapshot", copy.deepcopy(obj._data))
        return obj

    # -- change tracking ----------------------------------------------------
    def _take_snapshot(self):
        object.__setattr__(self, "_snapshot", copy.deepcopy(self._data))

    def _changed_fields(self) -> Dict[str, Any]:
        if self._snapshot is None:
            return dict(self._data)
        return {
            key: value
            for key, value in self._data.items()
            if self._snapshot.get(key, _MISSING) != value
        }

    # -- indexes ------------------------------------------------------------
    @classmethod
    def ensure_indexes(cls, database):
        collection = database[cls.__tablename__]
        for col in cls.__columns__.values():
            if col.primary_key:
                continue
            if col.unique:
                collection.create_index(col.name, unique=True)
            elif col.index or col.foreign_key is not None:
                collection.create_index(col.name)

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"<{type(self).__name__} id={self._data.get('id')}>"


def document_base():
    """Return the base class every document model inherits from."""
    return ModelBase


__all__ = [
    "Boolean",
    "BoundColumn",
    "Column",
    "Criterion",
    "DateTime",
    "Float",
    "ForeignKey",
    "Integer",
    "JSON",
    "ModelBase",
    "Order",
    "String",
    "Text",
    "and_",
    "document_base",
    "metadata",
    "not_",
    "or_",
    "relationship",
]
