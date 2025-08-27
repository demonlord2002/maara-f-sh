import os
import re
import time
import datetime
import asyncio
import io
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.enums import ParseMode
from pymongo import MongoClient
from config import *

# ---------------- MONGO DB ----------------
mongo = MongoClient(MONGO_URI)
db = mongo["file_share_bot"]
files_col = db["files"]
users_col = db["users"]

# ---------------- INIT BOT ----------------
app = Client(
    "file_share_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

BOT_USERNAME = os.getenv("BOT_USERNAME", "Madara_FSBot")

# ---------------- CANCEL FLAGS ----------------
cancel_flags = {}

# ---------------- ESCAPE MARKDOWN ----------------
def escape_markdown(text: str) -> str:
    return re.sub(r"([_*\[\]()~`>#+-=|{}.!])", r"\\\1", text)

# ---------------- FORCE SUBSCRIBE CHECK ----------------
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await app.get_chat_member(FORCE_SUBSCRIBE_CHANNEL, user_id)
        return member.status not in ["left", "kicked"]
    except:
        return False

# ---------------- PROGRESS BAR ----------------
async def progress_bar(current, total, start_time, message, prefix=""):
    now = time.time()
    elapsed = now - start_time
    if elapsed == 0: elapsed = 0.001
    speed = current / elapsed
    speed_text = f"{speed/1024/1024:.2f} MB/s"

    percentage = current / total * 100
    filled_length = int(20 * current // total)
    bar = "█" * filled_length + "—" * (20 - filled_length)

    text = (
        f"{prefix}\n"
        f"`[{bar}] {percentage:.1f}%`\n"
        f"Processed: {current/1024/1024:.2f}MB of {total/1024/1024:.2f}MB\n"
        f"Speed: {speed_text}\n"
        f"Elapsed: {int(elapsed)}s"
    )
    try:
        await message.edit_text(text)
    except:
        pass

# ---------------- START COMMAND ----------------
@app.on_message(filters.command("start"))
async def start(client, message):
    users_col.update_one(
        {"user_id": message.from_user.id},
        {"$set": {
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name
        }},
        upsert=True
    )

    if not await is_subscribed(message.from_user.id):
        await message.reply_text(
            "🚨 Access Restricted! Join our channel first.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel ✅", url=SUPPORT_LINK)],
                [InlineKeyboardButton("✅ Verify Joined", callback_data="verify_sub")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    await message.reply_text(
        f"👋 Hello {escape_markdown(message.from_user.first_name)}!\n\n"
        f"📂 Send me any file and I will create a secure shareable link for you.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Owner", url=f"https://t.me/{OWNER_USERNAME}"),
             InlineKeyboardButton("Support Channel", url=SUPPORT_LINK)]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

# ---------------- VERIFY ----------------
@app.on_callback_query(filters.regex("verify_sub"))
async def verify_subscription(client, callback_query):
    user_id = callback_query.from_user.id
    if await is_subscribed(user_id):
        await callback_query.message.edit_text("✅ Verification successful! You can now send files.")
    else:
        await callback_query.answer("❌ Not subscribed yet!", show_alert=True)

# ---------------- FILE HANDLER ----------------
@app.on_message(filters.document | filters.video | filters.audio)
async def handle_file(client, message):
    if not await is_subscribed(message.from_user.id):
        await message.reply_text(
            f"🚨 Join channel to use this bot!\n👉 {SUPPORT_LINK}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel ✅", url=SUPPORT_LINK)]])
        )
        return

    file_name = message.document.file_name if message.document else \
                message.video.file_name if message.video else \
                message.audio.file_name
    safe_file_name = escape_markdown(file_name)

    fwd_msg = await app.copy_message(DATABASE_CHANNEL, message.chat.id, message.id)

    file_record = {
        "file_id": fwd_msg.id,
        "chat_id": fwd_msg.chat.id,
        "user_id": message.from_user.id,
        "file_name": file_name,
        "timestamp": datetime.datetime.now(datetime.timezone.utc),
        "status": "active"
    }
    files_col.insert_one(file_record)

    users_col.update_one({"user_id": message.from_user.id}, {"$set": {"renaming_file_id": fwd_msg.id}})

    await message.reply_text(
        f"✏️ Send me the new file name.\n\n"
        f"You can reply with plain text or use the command:\n"
        f"/rename [NewFileName]\n\n"
        f"_Tip: If you omit the extension, I'll keep the original one._",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Support Channel ✅", url=SUPPORT_LINK)]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

# ---------------- RENAME HANDLER ----------------
async def perform_rename(user_id, new_name, message: Message):
    user_doc = users_col.find_one({"user_id": user_id})
    if not user_doc or "renaming_file_id" not in user_doc:
        return await message.reply_text("⚠️ First send a file and tap rename.")

    file_id = user_doc["renaming_file_id"]
    file_doc = files_col.find_one({"file_id": file_id})
    if not file_doc:
        return await message.reply_text("❌ Original file not found!")

    orig_ext = os.path.splitext(file_doc["file_name"])[1]
    if not new_name.endswith(orig_ext):
        new_name += orig_ext

    temp_dir = "/tmp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, new_name)

    try:
        orig_msg = await app.get_messages(file_doc["chat_id"], file_doc["file_id"])
        start_time = time.time()

        # ---------------- DOWNLOAD PROGRESS ----------------
        async def download_progress(current, total):
            await progress_bar(current, total, start_time, message, prefix="⏬ Downloading...")

        await app.download_media(orig_msg, file_name=temp_file_path, progress=download_progress)

        start_time = time.time()

        # ---------------- UPLOAD PROGRESS ----------------
        async def upload_progress(current, total):
            await progress_bar(current, total, start_time, message, prefix="⏫ Uploading...")

        sent_msg = await app.send_document(
            DATABASE_CHANNEL,
            temp_file_path,
            file_name=new_name,
            progress=upload_progress
        )

    except Exception as e:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return await message.reply_text(f"❌ Error: {str(e)}")

    files_col.update_one({"file_id": file_id}, {"$set": {"file_id": sent_msg.id, "chat_id": DATABASE_CHANNEL, "file_name": new_name}})
    file_link = f"https://t.me/{BOT_USERNAME}?start=file_{sent_msg.id}"

    await message.reply_text(
        f"✅ File successfully renamed ❤️\n\n"
        f"📂 File Name: {escape_markdown(new_name)}\n\n"
        f"🔗 Unique Shareable Link:\n{file_link}\n\n"
        f"⚠️ Note: This link is safe and temporary. File will be removed automatically after 10 minutes for security & copyright reasons.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Support Channel ✅", url=SUPPORT_LINK)]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)
    users_col.update_one({"user_id": user_id}, {"$unset": {"renaming_file_id": ""}})

# ---------------- RENAME COMMAND ----------------
@app.on_message(filters.command("rename"))
async def rename_command(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("❌ Usage: `/rename NewFileName`", quote=True)
    new_name = " ".join(message.command[1:])
    await perform_rename(message.from_user.id, new_name, message)

# ---------------- TEXT REPLY FOR RENAME ----------------
@app.on_message(filters.text & ~filters.command(["start","rename"]))
async def rename_text(client, message: Message):
    user_doc = users_col.find_one({"user_id": message.from_user.id})
    if not user_doc or "renaming_file_id" not in user_doc:
        return
    await perform_rename(message.from_user.id, message.text.strip(), message)

# ---------------- RUN BOT ----------------
print("🔥 Madara_FSBot running with progress bars...")
app.run()
