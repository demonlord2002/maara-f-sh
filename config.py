import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Convert comma-separated OWNER_IDS to list of ints
OWNER_IDS = list(map(int, os.getenv("OWNER_IDS").split(",")))

# NEW: Channel where files are saved (must be bot admin)
DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID"))
