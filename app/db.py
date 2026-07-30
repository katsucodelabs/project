from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


class Database:
    def __init__(self, uri: str, name: str) -> None:
        self.client = AsyncIOMotorClient(uri)
        self.db: AsyncIOMotorDatabase = self.client[name]

    async def init_indexes(self) -> None:
        await self.db.users.create_index("user_id", unique=True)
        await self.db.purchases.create_index("invoice", unique=True)
        await self.db.purchases.create_index([("user_id", 1), ("status", 1)])
        await self.db.settings.create_index("key", unique=True)

    async def upsert_user(self, user_id: int, data: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc)
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {**data, "last_seen_at": now}, "$setOnInsert": {"created_at": now, "is_vip": False}},
            upsert=True,
        )

    async def all_user_ids(self) -> list[int]:
        return [doc["user_id"] async for doc in self.db.users.find({}, {"user_id": 1})]

    async def set_setting(self, key: str, value: Any) -> None:
        await self.db.settings.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)

    async def get_setting(self, key: str, default: Any = None) -> Any:
        doc = await self.db.settings.find_one({"key": key})
        return doc["value"] if doc else default
