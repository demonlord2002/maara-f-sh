import os
import re

# ---------------- TELEGRAM BOT CONFIG ----------------
API_ID = int(os.getenv("API_ID", 22201946))
API_HASH = os.getenv("API_HASH", "f4e7f0de47a09671133ecafa6920ebbe")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8059320705:AAF7ECLVgkz5htAMOTbm1D6ILxRiok3RMBU")

# ---------------- CHANNELS & OWNER ----------------
DATABASE_CHANNEL = os.getenv("DATABASE_CHANNEL", "@dupnc")
FORCE_SUBSCRIBE_CHANNEL = os.getenv("FORCE_SUBSCRIBE_CHANNEL", "@BiggBossTamil9HD")

# OWNER_IDS supports multiple comma-separated IDs

OWNER_IDS = list(map(int, os.getenv("OWNER_IDS", "7813285237").split(",")))
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "MoviesNewHDTamil")
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/BiggBossTamil9HD")

# ---------------- MONGO DB ----------------
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://markusmarwin2002:markusmarwin2002@cluster0.cgidefq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)

# ---------------- OPTIONAL ----------------
WEB_URL = os.getenv("WEB_URL", None)  # Optional external URL for permanent links
