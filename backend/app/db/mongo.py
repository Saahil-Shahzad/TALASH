from __future__ import annotations

from typing import Any

from bson import ObjectId
from pymongo import MongoClient

from backend.app.core.config import settings


_client: MongoClient | None = None


def _get_client() -> MongoClient:
    global _client
    if _client is None:
        if not settings.MONGODB_URL:
            raise RuntimeError(
                "MONGODB_URL is not set. Create a .env file in the project root (or set the env var) and provide a valid MongoDB URI."
            )
        _client = MongoClient(settings.MONGODB_URL)
    return _client


def get_db():
    client = _get_client()
    # db = client.get_default_database()
    # if db is None:
    db = client[settings.MONGODB_DB_NAME]
    return db


def to_object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except Exception:
        return None


def normalize_mongo_doc(doc: dict[str, Any]) -> dict[str, Any]:
    if not doc:
        return doc
    payload = dict(doc)
    _id = payload.pop("_id", None)
    if _id is not None:
        payload["id"] = str(_id)
    return payload
