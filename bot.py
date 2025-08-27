from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from pymongo import MongoClient
from config import *
import datetime
import asyncio
import re
import os
import time

# ---------------- MONGO DB SETUP ----------------
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

# ---------------- CANCEL FLAGS ----------------
cancel_flags = {}  # user_id: True/False

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

# ---------------- SANITIZE FILENAME ----------------
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

# ---------------- PROGRESS BAR ----------------
def progress_bar(current, total, width=20):
    done = int(width * current / total) if total else 0
    remaining = width - done
    percent = (current / total * 100) if total else 0
    return f"[{'▓'*done}{'░'*remaining}] {percent:.2f}%"

async def progress_for_pyrogram(current, total, message, prefix=""):
    text = f"{prefix} {progress_bar(current, total)}"
    try:
        await message.edit_text(text)
    except:
        pass

# ---------------- START COMMAND ----------------
@app.on_message(filters.command("start"))
async def start(client, message):
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith("file_"):
        file_id = int(args[1].replace("file_", ""))
        file_doc = files_col.find_one({"file_id": file_id, "status": "active"})
        if file_doc:
            if not await is_subscribed(message.from_user.id):
                await message.reply_text(
                    f"🚨 Join channel first!\n👉 {SUPPORT_LINK}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel ✅", url=SUPPORT_LINK)]])
                )
                return
            await app.copy_message(
                chat_id=message.chat.id,
                from_chat_id=file_doc["chat_id"],
                message_id=file_doc["file_id"]
            )
            return
        else:
            await message.reply_text("❌ File not available.")
            return

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

    files_col.insert_one({
        "file_id": fwd_msg.id,
        "chat_id": fwd_msg.chat.id,
        "user_id": message.from_user.id,
        "file_name": file_name,
        "timestamp": datetime.datetime.now(datetime.timezone.utc),
        "status": "active"
    })

    await message.reply_text(
        f"✅ **File received!**\n\n"
        f"💡 **Do you want to rename before getting a shareable link?**\n\n"
        f"Original: `{safe_file_name}`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Yes, rename ✏️", callback_data=f"rename_{fwd_msg.id}")],
            [InlineKeyboardButton("No, give link 🔗", callback_data=f"link_{fwd_msg.id}")],
            [InlineKeyboardButton("Support Channel ✅", url=SUPPORT_LINK)]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

# ---------------- LINK CALLBACK ----------------
@app.on_callback_query(filters.regex(r"link_(\d+)"))
async def send_shareable_link(client, callback_query):
    file_id = int(callback_query.data.split("_")[1])
    file_doc = files_col.find_one({"file_id": file_id})
    if not file_doc:
        await callback_query.message.edit_text("❌ File not found!")
        return

    file_name = escape_markdown(file_doc["file_name"])
    file_link = f"https://t.me/Madara_FSBot?start=file_{file_id}"

    await callback_query.message.edit_text(
        f"✅ **File saved!**\n\n📂 File Name: {file_name}\n\n🔗 Shareable Link:\n{file_link}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗃️ Open File", url=file_link)]]),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

# ---------------- RENAME CALLBACK ----------------
@app.on_callback_query(filters.regex(r"rename_(\d+)"))
async def rename_file_prompt(client, callback_query):
    file_id = int(callback_query.data.split("_")[1])
    users_col.update_one({"user_id": callback_query.from_user.id}, {"$set": {"renaming_file_id": file_id}})

    await callback_query.message.edit_text(
        f"✏️ Send me the new file name.\n\n"
        f"Use plain text or /rename [NewFileName].\n"
        f"_Tip: If you omit the extension, I keep the original._",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Support Channel ✅", url=SUPPORT_LINK)]]),
        parse_mode=ParseMode.MARKDOWN
    )

# ---------------- PERFORM RENAME ----------------
async def perform_rename(user_id, new_name, message):
    user_doc = users_col.find_one({"user_id": user_id})
    if not user_doc or "renaming_file_id" not in user_doc:
        await message.reply_text("⚠️ First send a file and tap rename.")
        return

    file_id = user_doc["renaming_file_id"]
    file_doc = files_col.find_one({"file_id": file_id})
    if not file_doc:
        await message.reply_text("❌ Original file not found!")
        return

    # Sanitize filename
    new_name = sanitize_filename(new_name)
    orig_ext = os.path.splitext(file_doc["file_name"])[1]
    if not new_name.endswith(orig_ext):
        new_name += orig_ext

    os.makedirs("downloads", exist_ok=True)

    status_msg = await message.reply_text("📥 Downloading file...")
    orig_msg = await app.get_messages(file_doc["chat_id"], file_doc["file_id"])
    temp_file = await app.download_media(
        orig_msg,
        file_name=f"downloads/{new_name}",
        progress=lambda c, t: asyncio.create_task(progress_for_pyrogram(c, t, status_msg, prefix="📥 Downloading:"))
    )

    if not temp_file:
        await status_msg.edit_text("❌ Download failed. Try again.")
        return

    await status_msg.edit_text("📤 Uploading file...")
    sent_msg = await app.send_document(
        DATABASE_CHANNEL,
        temp_file,
        file_name=new_name,
        progress=lambda c, t: asyncio.create_task(progress_for_pyrogram(c, t, status_msg, prefix="📤 Uploading:"))
    )

    files_col.update_one({"file_id": file_id}, {"$set": {"file_id": sent_msg.id, "chat_id": DATABASE_CHANNEL, "file_name": new_name}})
    file_link = f"https://t.me/Madara_FSBot?start=file_{sent_msg.id}"

    await status_msg.edit_text(
        f"✅ **File renamed & saved!**\n\n📂 New Name: {escape_markdown(new_name)}\n\n🔗 Shareable Link:\n{file_link}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗃️ Open File", url=file_link)],
            [InlineKeyboardButton("Support Channel ✅", url=SUPPORT_LINK)]
        ]),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

    os.remove(temp_file)
    users_col.update_one({"user_id": user_id}, {"$unset": {"renaming_file_id": ""}})

# ---------------- RENAME COMMAND ----------------
@app.on_message(filters.command("rename"))
async def rename_command(client, message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text("Usage: /rename NewFileName")
        return
    await perform_rename(message.from_user.id, parts[1].strip(), message)

@app.on_message(filters.text & ~filters.command(["start","rename"]))
async def rename_text(client, message):
    user_doc = users_col.find_one({"user_id": message.from_user.id})
    if user_doc and "renaming_file_id" in user_doc:
        await perform_rename(message.from_user.id, message.text.strip(), message)

# ---------------- RUN BOT ----------------
print("🔥 File Sharing Bot running with live progress bars...")
app.run()
