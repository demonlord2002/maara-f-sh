# 🩸 Madara Uchiha File Share Bot - Full Updated Version with MongoDB & Force Subscribe

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
import os, time, re, asyncio, subprocess
from dotenv import load_dotenv
from pyrogram.errors import UserNotParticipant, FloodWait

# Load environment variables
load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_IDS = list(map(int, os.getenv("OWNER_IDS").split(",")))
# DB_CHANNEL_ID can be int or username
db_channel_env = os.getenv("DB_CHANNEL_ID", "madara_db_test")
try:
    DB_CHANNEL_ID = int(db_channel_env)  # Try converting to int
except ValueError:
    DB_CHANNEL_ID = db_channel_env      # If fails, use as username

MONGO_URL = os.getenv("MONGO_URL")
FORCE_CHANNEL = os.getenv("FORCE_CHANNEL", "Fallen_Angels_Team")

# Connect to MongoDB
mongo = MongoClient(MONGO_URL)
db = mongo["madara_bot"]
files_col = db["files"]
users_col = db["users"]

# Initialize bot
app = Client("madara_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ================= Utility Functions ===================
def get_duration_seconds(start, end):
    def to_sec(t): return sum(x * int(t) for x, t in zip([3600, 60, 1], t.split(":")))
    return to_sec(end) - to_sec(start)

async def is_subscribed(client, user_id):
    try:
        member = await client.get_chat_member(FORCE_CHANNEL, user_id)
        return member.status != "left"
    except UserNotParticipant:
        return False
    except:
        return False

async def force_subscribe_check(client, message: Message):
    if not await is_subscribed(client, message.from_user.id):
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Join Support Channel ✅", url=f"https://t.me/{FORCE_CHANNEL}")]]
        )
        await message.reply(f"🚨 You must join our channel @{FORCE_CHANNEL} to use this bot.", reply_markup=kb)
        return False
    return True

# Decorator for force subscribe
def require_subscription(func):
    async def wrapper(client, message: Message):
        if not await force_subscribe_check(client, message):
            return
        return await func(client, message)
    return wrapper

# =================== User Tracking =====================
@app.on_message(filters.private)
async def save_user(client, message: Message):
    users_col.update_one(
        {"_id": message.from_user.id},
        {"$set": {"username": message.from_user.username, "first_name": message.from_user.first_name}},
        upsert=True
    )

# =================== /start Command ====================
@app.on_message(filters.private & filters.command("start"))
@require_subscription
async def start_cmd(client, message: Message):
    args = message.text.split()
    if len(args) == 2:
        file_id = args[1]
        data = files_col.find_one({"_id": file_id})
        if data:
            await client.copy_message(chat_id=message.chat.id, from_chat_id=data["chat_id"], message_id=data["msg_id"])
            notice = await client.send_message(
                message.chat.id,
                "⚠️ **Notice:** This file is copyrighted.\nAuto-delete in 10 minutes.\n❌ No screenshots ❌ No forwarding",
                parse_mode="markdown"
            )
            await asyncio.sleep(600)
            try:
                await client.delete_messages(chat_id=message.chat.id, message_ids=[data["msg_id"], notice.id])
            except: pass
        else:
            await message.reply("❌ File not found or expired.")
        return

    kb = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("👑 Owner", url="https://t.me/SunsetOfMe"),
            InlineKeyboardButton("💬 Help", callback_data="help"),
            InlineKeyboardButton("📢 Support Channel", url=f"https://t.me/{FORCE_CHANNEL}")
        ]]
    )
    await message.reply(
        "🩸 **Madara Uchiha File Share Bot**\n\n"
        "Drop your files like a shinobi, share like a legend 💀\n"
        "All Uchihas must join the Support Channel to generate links.",
        reply_markup=kb,
        parse_mode="markdown"
    )

# =================== Help Button =======================
@app.on_callback_query(filters.regex("help"))
async def help_callback(client, callback_query):
    await callback_query.answer()
    await callback_query.message.edit(
        "**🩸 MADARA UCHIHA - COMMAND SCROLL ⚔️**\n\n"
        "**USER COMMANDS:**\n"
        "🧿 /start – Access shared files using links\n"
        "📎 Send a file – Get a secret sharing link\n\n"
        "**OWNER COMMANDS:**\n"
        "✂️ /sample HH:MM:SS to HH:MM:SS – Trim sample from replied video (Owner only)\n"
        "👥 /addusers <id> – Grant special access\n"
        "🚫 /delusers <id> – Revoke a user\n"
        "📜 /getusers – Show all allowed users\n"
        "📢 /broadcast <msg> – DM all active users\n\n"
        "⚠️ Files are auto-deleted after 10 mins. ❌ No screenshots ❌ No forwarding"
    )

# =================== Save Files ========================
@app.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
@require_subscription
async def save_file(client, message: Message):
    file_id = str(message.id)
    saved = await message.copy(chat_id=DB_CHANNEL_ID)
    files_col.update_one({"_id": file_id}, {"$set": {"chat_id": DB_CHANNEL_ID, "msg_id": saved.id}}, upsert=True)
    link = f"https://t.me/{(await app.get_me()).username}?start={file_id}"
    await message.reply(
        f"✅ File sealed!\n📎 Link: {link}\n\n⚠️ Auto-delete in 10 mins. No screenshot/no forwarding.",
        parse_mode="markdown"
    )

# =================== Sample Trim =======================
@app.on_message(filters.private & filters.command("sample"))
async def sample_trim(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only the owner can use /sample.")
    if not message.reply_to_message or not (message.reply_to_message.video or message.reply_to_message.document):
        return await message.reply("⚠️ Please reply to a video with:\n/sample HH:MM:SS to HH:MM:SS")
    match = re.search(r"(\d{2}:\d{2}:\d{2})\s+to\s+(\d{2}:\d{2}:\d{2})", message.text)
    if not match:
        return await message.reply("❌ Invalid format. Use:\n/sample 00:10:00 to 00:10:30")
    start, end = match.group(1), match.group(2)
    duration = get_duration_seconds(start, end)
    if duration <= 0 or duration > 60:
        return await message.reply("⚠️ Duration must be 1–60 seconds.")
    msg = await message.reply("📥 Downloading video...")
    try:
        input_path = await message.reply_to_message.download()
    except:
        return await msg.edit("❌ Download failed.")
    output_path = "sample_clip.mp4"
    await msg.edit("✂️ Trimming sample video (fast mode)...")
    fast_cmd = ["ffmpeg", "-ss", start, "-i", input_path, "-t", str(duration), "-c", "copy", output_path, "-y"]
    process = await asyncio.create_subprocess_exec(*fast_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    await process.communicate()
    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        await msg.edit("⚠️ Fast trim failed, retrying with safe mode...")
        slow_cmd = ["ffmpeg", "-i", input_path, "-ss", start, "-t", str(duration), "-c:v", "libx264", "-c:a", "aac", output_path, "-y"]
        process = await asyncio.create_subprocess_exec(*slow_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        await process.communicate()
    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        os.remove(input_path)
        return await msg.edit("❌ Failed to generate sample.")
    await msg.edit("📤 Uploading sample...")
    await client.send_video(chat_id=message.chat.id, video=output_path, caption=f"✂️ Sample clip {start} to {end}")
    os.remove(input_path)
    os.remove(output_path)

# =================== Broadcast =========================
@app.on_message(filters.private & filters.command("broadcast"))
async def broadcast(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only the owner can use /broadcast.")

    if len(message.command) < 2 and not message.reply_to_message:
        return await message.reply("⚠️ Usage:\n/broadcast Your message\nOr reply to a file/video/document/photo to broadcast.")

    all_users = list(users_col.find({}))
    if not all_users:
        return await message.reply("⚠️ No users to broadcast.")

    reply_msg = message.reply_to_message
    success, failed = 0, 0
    msg_status = await message.reply(f"🚀 Broadcasting to {len(all_users)} users...")

    for user in all_users:
        user_id = user["_id"]
        try:
            if reply_msg:
                if reply_msg.text:
                    await client.send_message(user_id, reply_msg.text)
                elif reply_msg.photo:
                    await client.send_photo(user_id, photo=await reply_msg.download(), caption=reply_msg.caption)
                elif reply_msg.video:
                    await client.send_video(user_id, video=await reply_msg.download(), caption=reply_msg.caption)
                elif reply_msg.document:
                    await client.send_document(user_id, document=await reply_msg.download(), caption=reply_msg.caption)
                elif reply_msg.audio:
                    await client.send_audio(user_id, audio=await reply_msg.download(), caption=reply_msg.caption)
            else:
                text_to_send = message.text.split(None, 1)[1]
                await client.send_message(user_id, text_to_send)
            success += 1
            await asyncio.sleep(0.5)
        except:
            failed += 1
            continue

    await msg_status.edit(f"✅ Broadcast completed!\nSuccess: {success}\nFailed: {failed}")

# =================== Bot Start =========================
print("🩸 MADARA FILE SHARE BOT - Full Updated Version Summoning...")
app.run()
