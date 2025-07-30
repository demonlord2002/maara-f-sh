import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_IDS = list(map(int, os.getenv("OWNER_IDS").split(",")))

# File database channel (make sure it's an integer, NOT a string with @)
DB_CHANNEL = int(os.getenv("DB_CHANNEL"))  # use this in bot.py

# MongoDB URI (optional)
MONGO_URL = os.getenv("MONGO_URL")
