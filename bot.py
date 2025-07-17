import os
import re
import asyncio
import logging
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient

# 🩸 LOGGING SYSTEM
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ⚙️ ENVIRONMENT VARIABLES
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
DB_CHANNEL_ID = os.getenv("DB_CHANNEL_ID")
BOT_USERNAME = "Madara_FSBot"

# 🔗 DATABASE SETUP
client = MongoClient(MONGO_URL)
db = client["madara_bot"]
users_col = db["users"]

# 🔧 BOT SETUP
app = Client("madara_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ⏳ CHECK USER ACCESS

def is_active(user_id: int) -> bool:
    user = users_col.find_one({"_id": user_id})
    if not user:
        return False
    return user.get("expiry", datetime.utcnow()) > datetime.utcnow()

# ➕ ADD USER

def add_user(user_id: int):
    expiry = datetime.utcnow() + timedelta(days=28)
    users_col.update_one({"_id": user_id}, {"$set": {"expiry": expiry}}, upsert=True)

# ❌ REMOVE USER

def del_user(user_id: int):
    users_col.delete_one({"_id": user_id})

# 📜 GET ALL USERS

def get_all_users():
    return users_col.find()

# 🚀 START COMMAND
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    user_id = message.from_user.id
    args = message.text.split(" ", 1)

    if len(args) > 1 and args[1].startswith("batch_"):
        # 🎯 Handle batch start link
        parts = args[1][6:].split("_")
        if len(parts) != 2:
            return await message.reply("❌ Invalid batch link format.")

        first_id, last_id = map(int, parts)
        links = []
        for msg_id in range(first_id, last_id + 1):
            links.append(f"https://t.me/c/{str(DB_CHANNEL_ID)[4:]}/{msg_id}")

        text = "**📂 Your batch files:**\n\n" + "\n".join(links)
        return await message.reply(text, disable_web_page_preview=True)

    await message.reply(
        "👋 Welcome to *Madara Uchiha File Share Bot*\n\n"
        "📁 Just send me a file to get a **secret link**\n"
        "✂️ Use `/sample HH:MM:SS to HH:MM:SS` on a video to get a sample\n"
        "📦 Use /batch to create a share link for episodes\n\n"
        "🛡 Only Uchihas can access the power."
    )

# 📥 FILE UPLOAD HANDLER
@app.on_message(filters.document | filters.video & filters.private)
async def file_handler(client, message: Message):
    if not is_active(message.from_user.id):
        return await message.reply("🚫 Plan expired. Contact @Madara_Uchiha_lI")

    sent = await message.forward(DB_CHANNEL_ID)
    file_id = sent.message_id
    share_link = f"https://t.me/{BOT_USERNAME}?start={file_id}"

    await message.reply(
        f"✅ File stored!\n\n🔗 Share Link: {share_link}",
        disable_web_page_preview=True
    )

# 🔗 HANDLE FILE LINK
@app.on_message(filters.command("start") & filters.private & filters.regex(r"\d+$"))
async def get_shared_file(client, message: Message):
    msg_id = int(message.text.split()[-1])
    try:
        await client.copy_message(
            chat_id=message.chat.id,
            from_chat_id=DB_CHANNEL_ID,
            message_id=msg_id
        )
    except Exception:
        await message.reply("❌ File not found or expired. This message only get bot not file 🗃️ 🥺")

# 📦 /batch - Create a sharable batch link from channel posts
@app.on_message(filters.command("batch") & filters.private)
async def batch_cmd(client, message: Message):
    if not is_active(message.from_user.id):
        return await message.reply("🚫 Plan expired. Contact @Madara_Uchiha_lI")

    await message.reply("📥 Give me the **first message link** from your batch channel.")

    def link_filter(msg):
        return bool(re.search(r"t\.me/c/\d+/\d+", msg.text or ""))

    try:
        first = await client.listen(message.chat.id, filters=link_filter, timeout=60)
        first_link = first.text.strip()

        match_first = re.search(r"t\.me/c/(\d+)/(\d+)", first_link)
        if not match_first:
            return await first.reply("❌ Invalid first link format. Use t.me/c/...")

        await first.reply("📥 Now give me the **last message link** from your batch channel.")
        last = await client.listen(message.chat.id, filters=link_filter, timeout=60)
        last_link = last.text.strip()

        match_last = re.search(r"t\.me/c/(\d+)/(\d+)", last_link)
        if not match_last:
            return await last.reply("❌ Invalid last link format. Use t.me/c/...")

        first_msg_id = match_first.group(2)
        last_msg_id = match_last.group(2)

        batch_link = f"https://t.me/{BOT_USERNAME}?start=batch_{first_msg_id}_{last_msg_id}"

        await last.reply(
            f"✅ Batch created successfully!\n📎 Link: {batch_link}",
            disable_web_page_preview=True
        )

    except asyncio.TimeoutError:
        await message.reply("⏳ Timeout. You didn’t reply in time.")

# ✂️ /sample - Trim sample from replied video
@app.on_message(filters.command("sample") & filters.private)
async def sample_cmd(client, message: Message):
    await message.reply("⚙️ Feature under development.")

# 🧾 /status - Check remaining time
@app.on_message(filters.command("status") & filters.private)
async def status_cmd(client, message: Message):
    user = users_col.find_one({"_id": message.from_user.id})
    if not user:
        return await message.reply("❌ You're not in the database.")

    remaining = user["expiry"] - datetime.utcnow()
    days = remaining.days
    await message.reply(f"⏳ You have {days} day(s) left.")

# 🔐 ADMIN COMMANDS
@app.on_message(filters.command("addusers") & filters.user([os.getenv("OWNER_ID")]))
async def addusers_cmd(client, message: Message):
    if len(message.command) != 2:
        return await message.reply("❌ Usage: /addusers <user_id>")
    user_id = int(message.command[1])
    add_user(user_id)
    await message.reply(f"✅ Added {user_id} for 28 days")

@app.on_message(filters.command("delusers") & filters.user([os.getenv("OWNER_ID")]))
async def delusers_cmd(client, message: Message):
    if len(message.command) != 2:
        return await message.reply("❌ Usage: /delusers <user_id>")
    user_id = int(message.command[1])
    del_user(user_id)
    await message.reply(f"🚫 Removed {user_id} from access")

@app.on_message(filters.command("getusers") & filters.user([os.getenv("OWNER_ID")]))
async def getusers_cmd(client, message: Message):
    text = "👥 Active Users:\n"
    for user in get_all_users():
        text += f"`{user['_id']}` - Expires: {user['expiry'].strftime('%Y-%m-%d')}\n"
    await message.reply(text)

@app.on_message(filters.command("broadcast") & filters.user([os.getenv("OWNER_ID")]))
async def broadcast_cmd(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("❌ Usage: /broadcast <message>")

    text = message.text.split(None, 1)[1]
    success = 0
    for user in get_all_users():
        try:
            await client.send_message(user['_id'], text)
            success += 1
        except:
            pass
    await message.reply(f"📢 Broadcast complete. Reached {success} users.")

# 📜 /help - List all commands
@app.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message: Message):
    await message.reply(
        "**🩸 MADARA UCHIHA - COMMAND SCROLL ⚔️**\n\n"
        "**👤 USER COMMANDS:**\n"
        "🧿 /start – Access shared files using links\n"
        "⏳ /status – Check your remaining plan time\n"
        "📎 *Send a file* – Get a secret sharing link\n"
        "✂️ /sample HH:MM:SS to HH:MM:SS – Trim sample from replied video\n"
        "📦 /batch – Create a single share link from batch messages\n\n"
        "**👑 OWNER COMMANDS:**\n"
        "👥 /addusers  – Grant 28 days access\n"
        "🚫 /delusers  – Revoke a user\n"
        "📜 /getusers – Show all allowed users\n"
        "📢 /broadcast  – DM all active users\n\n"
        "🔐 *Only true Uchihas can rule the darkness.*"
    )

# 🚀 RUN THE BOT
print("🩸 MADARA FILE SHARE BOT with MongoDB is summoning forbidden chakra...")
app.run()
