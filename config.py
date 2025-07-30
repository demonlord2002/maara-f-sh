import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Owner(s)
OWNER_IDS = list(map(int, os.getenv("OWNER_IDS").split(",")))

# File database channel (from .env)
DB_CHANNEL = int(os.getenv("DB_CHANNEL"))

# MongoDB URI (from .env)
MONGO_URL = os.getenv("MONGO_URL")
