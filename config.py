import os
from dotenv import load_dotenv

# Load .env file from the same directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

class Config:
    # ---------------- Telegram API Credentials ----------------
    API_ID = int(os.getenv("API_ID", "0"))  # Replace 0 with your API_ID
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")

    # ---------------- Owner IDs ----------------
    # Comma-separated user IDs in .env
    OWNER_IDS = list(map(int, os.getenv("OWNER_IDS", "").split(",")))

    # ---------------- Database ----------------
    DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID", "0"))  # Telegram channel ID where files are stored
    MONGO_URL = os.getenv("MONGO_URL", "")  # MongoDB URI

    # ---------------- Force Subscribe Channel ----------------
    FORCE_CHANNEL = os.getenv("FORCE_CHANNEL", "Fallen_Angels_Team")  # Channel username
