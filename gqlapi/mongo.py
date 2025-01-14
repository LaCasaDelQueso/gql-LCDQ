# import tempfile
from motor.motor_asyncio import AsyncIOMotorClient
from gqlapi.config import MONGO_DB_NAME, MONGO_URI

mongo_db = AsyncIOMotorClient(
    MONGO_URI,
)[MONGO_DB_NAME]
