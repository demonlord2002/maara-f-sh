import re
from os import environ

# ---------------- TELEGRAM BOT CONFIG ----------------
API_ID = int(environ.get("API_ID", 22201946))  
API_HASH = environ.get("API_HASH", "f4e7f0de47a09671133ecafa6920ebbe")
BOT_TOKEN = environ.get("BOT_TOKEN", "7535712545:AAHFTW9Adh530PCqTXbqzsgWiQpL7ZUTrWM")

# ---------------- CHANNELS & OWNER ----------------
DATABASE_CHANNEL = environ.get("DATABASE_CHANNEL", "@madara_db_test")
FORCE_SUBSCRIBE_CHANNEL = environ.get("FORCE_SUBSCRIBE_CHANNEL", "@Fallen_Angels_Team")

OWNER_IDS = [int(x) for x in environ.get("OWNER_IDS", "7813285237").split()]
OWNER_USERNAME = environ.get("OWNER_USERNAME", "SunsetOfMe")
SUPPORT_LINK = environ.get("SUPPORT_LINK", "https://t.me/Fallen_Angels_Team")

# ---------------- MONGO DB ----------------
MONGO_URI = environ.get("MONGO_URI", "mongodb+srv://rubesh08virat:rubesh08virat@cluster0.d33p1rm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
