"""
MongoDB database operations using Motor (async driver).
Supports MongoDB Atlas (cloud) connections.
"""
import logging
from typing import Optional, List, Dict, Any

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError

from app.config import config

logger = logging.getLogger(__name__)


class Database:
    """Async MongoDB database handler for Atlas (cloud) or local."""
    
    _client: Optional[AsyncIOMotorClient] = None
    
    @classmethod
    async def connect(cls) -> None:
        """Connect to MongoDB Atlas and setup indexes."""
        try:
            # Connect with TLS for Atlas
            cls._client = AsyncIOMotorClient(
                config.MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
            )
            
            # Verify connection
            await cls._client.admin.command("ping")
            
            # Mask password in log
            safe_uri = config.MONGODB_URI
            if "@" in safe_uri:
                safe_uri = safe_uri.split("@")[1]
            logger.info(f"Connected to MongoDB: ...@{safe_uri}")
            
            # Create unique index on name+address
            collection = cls._get_collection()
            await collection.create_index(
                [("name", 1), ("address", 1)],
                unique=True,
                name="unique_name_address"
            )
            logger.info("Database indexes ensured")
            
        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise
    
    @classmethod
    async def disconnect(cls) -> None:
        """Close MongoDB connection."""
        if cls._client:
            cls._client.close()
            cls._client = None
            logger.info("Disconnected from MongoDB")
    
    @classmethod
    def _get_collection(cls):
        """Get the restaurants collection."""
        if not cls._client:
            raise RuntimeError("Database not connected")
        return cls._client[config.DATABASE_NAME][config.COLLECTION_NAME]
    
    @classmethod
    async def insert_restaurant(cls, restaurant: Dict[str, Any]) -> bool:
        """
        Insert restaurant if not exists.
        Returns True if inserted, False if duplicate.
        """
        try:
            await cls._get_collection().insert_one(restaurant)
            return True
        except DuplicateKeyError:
            return False
    
    @classmethod
    async def find_restaurants(cls, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find restaurants matching query, excluding _id field."""
        cursor = cls._get_collection().find(query, {"_id": 0})
        return await cursor.to_list(length=None)
    
    @classmethod
    async def count(cls) -> int:
        """Count total restaurants."""
        return await cls._get_collection().count_documents({})
    
    @classmethod
    async def clear(cls) -> int:
        """Delete all restaurants. Returns count deleted."""
        result = await cls._get_collection().delete_many({})
        return result.deleted_count
