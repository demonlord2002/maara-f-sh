import os
from dotenv import load_dotenv

# Load .env file from same directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

class Config:
    # Telegram API credentials
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    # Owner user IDs (comma-separated in .env)
    OWNER_IDS = list(map(int, os.getenv("OWNER_IDS", "").split(",")))

    # File storage channel ID (must be -100xxxxxxxxxxxx)
    DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID"))

    # MongoDB connection string
    MONGO_URL = os.getenv("MONGO_URL")
  
