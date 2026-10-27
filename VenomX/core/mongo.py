"""MongoDB adapter with a no-database fallback.

If MongoDB is absent/unreachable at startup, the bot can start with in-memory
no-op collections. Database-backed features will return empty/default results
and will not persist data until a real database is available.
"""
import os

from motor.motor_asyncio import AsyncIOMotorClient as _mongo_client_
from pymongo import MongoClient

import config
from ..logging import LOGGER

DB_NAME = "queen"


class _Result:
    acknowledged = True
    matched_count = 0
    modified_count = 0
    deleted_count = 0
    upserted_id = None
    inserted_id = None


class _SyncCursor:
    def __init__(self, items=None):
        self.items = list(items or [])

    def sort(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def skip(self, *args, **kwargs):
        return self

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, item):
        return self.items[item]


class _AsyncCursor:
    def __init__(self, items=None):
        self.items = list(items or [])

    def sort(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def skip(self, *args, **kwargs):
        return self

    async def to_list(self, length=None):
        return self.items if length is None else self.items[:length]

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self._index]
        self._index += 1
        return item


class _NoMongoSyncCollection:
    def find_one(self, *args, **kwargs):
        return None

    def find(self, *args, **kwargs):
        return _SyncCursor()

    def insert_one(self, *args, **kwargs):
        return _Result()

    def insert_many(self, *args, **kwargs):
        return _Result()

    def update_one(self, *args, **kwargs):
        return _Result()

    def update_many(self, *args, **kwargs):
        return _Result()

    def replace_one(self, *args, **kwargs):
        return _Result()

    def delete_one(self, *args, **kwargs):
        return _Result()

    def delete_many(self, *args, **kwargs):
        return _Result()

    def count_documents(self, *args, **kwargs):
        return 0

    def distinct(self, *args, **kwargs):
        return []

    def aggregate(self, *args, **kwargs):
        return _SyncCursor()


class _NoMongoAsyncCollection:
    async def find_one(self, *args, **kwargs):
        return None

    def find(self, *args, **kwargs):
        return _AsyncCursor()

    async def insert_one(self, *args, **kwargs):
        return _Result()

    async def insert_many(self, *args, **kwargs):
        return _Result()

    async def update_one(self, *args, **kwargs):
        return _Result()

    async def update_many(self, *args, **kwargs):
        return _Result()

    async def replace_one(self, *args, **kwargs):
        return _Result()

    async def delete_one(self, *args, **kwargs):
        return _Result()

    async def delete_many(self, *args, **kwargs):
        return _Result()

    async def count_documents(self, *args, **kwargs):
        return 0

    async def distinct(self, *args, **kwargs):
        return []

    def aggregate(self, *args, **kwargs):
        return _AsyncCursor()


class _NoMongoDatabase:
    def __init__(self, async_mode=False):
        self._async_mode = async_mode
        self._collections = {}

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._collections:
            cls = _NoMongoAsyncCollection if self._async_mode else _NoMongoSyncCollection
            self._collections[name] = cls()
        return self._collections[name]

    def __getitem__(self, name):
        return getattr(self, name)


def _fallback(reason):
    LOGGER(__name__).warning(
        "MongoDB is unavailable; starting with no-op database collections. "
        "Database-backed features will not persist data. Reason: %s",
        reason,
    )
    return _NoMongoDatabase(async_mode=True), _NoMongoDatabase(async_mode=False)


mongodb = None
pymongodb = None
_clients = []

# An explicit DISABLE_MONGODB=1 is useful when MongoDB is intentionally off.
if os.getenv("DISABLE_MONGODB", "").strip().lower() in {"1", "true", "yes"}:
    mongodb, pymongodb = _fallback("DISABLE_MONGODB is enabled")
elif not config.MONGO_DB_URI:
    # Keep the legacy shared database option, but don't terminate the process
    # when neither URI is available.
    temp_uri = os.getenv("TEMP_MONGO_DB_URI")
    if temp_uri:
        uri = temp_uri
        namespace = f"venom_{(config.BOT_TOKEN or '').split(':')[0]}" if config.BOT_TOKEN else "venom_bot"
    else:
        mongodb, pymongodb = _fallback("no MONGO_DB_URI or TEMP_MONGO_DB_URI configured")
        uri = None
        namespace = None

    if uri:
        try:
            async_client = _mongo_client_(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
            sync_client = MongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
            sync_client.admin.command("ping")
            _clients.extend([async_client, sync_client])
            mongodb = async_client[namespace or DB_NAME]
            pymongodb = sync_client[namespace or DB_NAME]
            LOGGER(__name__).info("MongoDB connection verified.")
        except Exception as exc:
            try:
                sync_client.close()
            except Exception:
                pass
            try:
                async_client.close()
            except Exception:
                pass
            mongodb, pymongodb = _fallback(exc)
else:
    try:
        async_client = _mongo_client_(
            config.MONGO_DB_URI, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000
        )
        sync_client = MongoClient(
            config.MONGO_DB_URI, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000
        )
        sync_client.admin.command("ping")
        _clients.extend([async_client, sync_client])
        mongodb = async_client[DB_NAME]
        pymongodb = sync_client[DB_NAME]
        LOGGER(__name__).info("MongoDB connection verified.")
    except Exception as exc:
        try:
            sync_client.close()
        except Exception:
            pass
        try:
            async_client.close()
        except Exception:
            pass
        mongodb, pymongodb = _fallback(exc)
