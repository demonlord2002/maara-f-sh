# database.py

from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")

client = AsyncIOMotorClient(MONGO_URL)
db = client["MadrasFileBot"]

# Collection for batches
batches = db["batches"]

async def save_batch(batch_id, files, uploader_id):
    await batches.insert_one({
        "_id": batch_id,
        "files": files,
        "uploader_id": uploader_id,
        "timestamp": datetime.utcnow()
    })

async def get_batch(batch_id):
    return await batches.find_one({"_id": batch_id})
