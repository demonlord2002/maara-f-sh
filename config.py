# config.py

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Owner(s) - comma-separated Telegram user IDs
OWNER_IDS = list(map(int, os.getenv("OWNER_IDS").split(",")))

# File database channel (username or channel ID with -100 prefix)
DB_CHANNEL_ID = -1002718440283  # e.g., "madara_db_test" or "-1001234567890"

# MongoDB URI
MONGO_URI = "mongodb+srv://xarwin2:xarwin2002@cluster0.qmetx2m.mongodb.net/?retryWrites=true&w=majority"  # Optional, only if using MongoDB
