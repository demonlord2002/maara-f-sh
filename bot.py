from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from pymongo import MongoClient
from config import *
import datetime
import asyncio
import re
import os

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

# ---------------- FORCE SUBSCRIBE CHECK ----------------
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await app.get_chat_member(FORCE_SUBSCRIBE_CHANNEL, user_id)
        return member.status not in ["left", "kicked"]
    except:
        return False

# Escape markdown special characters
def escape_markdown(text: str) -> str:
    return re.sub(r"([_*\[\]()~`>#+-=|{}.!])", r"\\\1", text)

# ---------------- PROGRESS FUNCTION ----------------
async def progress(current, total, message, prefix=""):
    try:
        percent = current * 100 / total
        await message.edit_text(f"{prefix} {percent:.1f}% ({current/1024:.1f}KB/{total/1024:.1f}KB)")
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
                    f"🚨 To access this file, join our channel first!\n👉 {SUPPORT_LINK}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel ✅", url=SUPPORT_LINK)]])
                )
                return
            sent_msg = await app.copy_message(
                chat_id=message.chat.id,
                from_chat_id=file_doc["chat_id"],
                message_id=file_doc["file_id"]
            )
            asyncio.create_task(auto_delete_file(message.chat.id, sent_msg.id, file_id))
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
            f"🚨 Access Restricted! Join our channel first.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel ✅", url=SUPPORT_LINK)],
                [InlineKeyboardButton("✅ Verify Joined", callback_data="verify_sub")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    await message.reply_text(
        f"👋 Hello {escape_markdown(message.from_user.first_name)}!\nSend me any file and I will create a safe shareable link.",
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
            f"🚨 Join our channel to use this bot!\n👉 {SUPPORT_LINK}",
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

    await message.reply_text(
        f"✅ File received!\n\nDo you want to **rename** before getting a shareable link?\n\nOriginal: `{safe_file_name}`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Yes, rename ✏️", callback_data=f"rename_{fwd_msg.id}")],
            [InlineKeyboardButton("No, give link 🔗", callback_data=f"link_{fwd_msg.id}")]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

# ---------------- RENAME CALLBACK ----------------
@app.on_callback_query(filters.regex(r"rename_(\d+)"))
async def rename_file_prompt(client, callback_query):
    file_id = int(callback_query.data.split("_")[1])
    users_col.update_one(
        {"user_id": callback_query.from_user.id},
        {"$set": {"renaming_file_id": file_id}}
    )
    await callback_query.message.edit_text("✏️ Send me the new file name (with extension) for your file.")

# ---------------- HANDLE RENAME & RE-UPLOAD ----------------
@app.on_message(filters.text)
async def handle_rename(client, message):
    user_doc = users_col.find_one({"user_id": message.from_user.id})
    if not user_doc or "renaming_file_id" not in user_doc:
        return

    file_id = user_doc["renaming_file_id"]
    new_name = message.text.strip()
    file_doc = files_col.find_one({"file_id": file_id})
    if not file_doc:
        await message.reply_text("❌ Original file not found!")
        return

    temp_file = await app.download_media(file_doc["chat_id"], file_doc["file_id"], file_name=new_name,
                                         progress=lambda c, t: asyncio.create_task(progress(c, t, message, "Downloading:")))

    # Re-upload to database channel
    if temp_file.endswith((".mp4", ".mkv", ".mov")):
        sent_msg = await app.send_video(DATABASE_CHANNEL, temp_file, progress=lambda c, t: asyncio.create_task(progress(c, t, message, "Uploading:")))
    elif temp_file.endswith((".mp3", ".m4a", ".wav")):
        sent_msg = await app.send_audio(DATABASE_CHANNEL, temp_file, progress=lambda c, t: asyncio.create_task(progress(c, t, message, "Uploading:")))
    else:
        sent_msg = await app.send_document(DATABASE_CHANNEL, temp_file, progress=lambda c, t: asyncio.create_task(progress(c, t, message, "Uploading:")))

    # Save new file record
    files_col.update_one({"file_id": file_id}, {"$set": {"file_id": sent_msg.id, "chat_id": DATABASE_CHANNEL, "file_name": new_name}})

    file_link = f"https://t.me/Madara_FSBot?start=file_{sent_msg.id}"

    await message.reply_text(
        f"✅ File saved!\n\n📂 File Name: {escape_markdown(new_name)}\n\n🔗 Unique Shareable Link:\n{file_link}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Open File", url=file_link)]]),
        parse_mode=ParseMode.MARKDOWN
    )

    os.remove(temp_file)
    users_col.update_one({"user_id": message.from_user.id}, {"$unset": {"renaming_file_id": ""}})

# ---------------- LINK CALLBACK ----------------
@app.on_callback_query(filters.regex(r"link_(\d+)"))
async def send_shareable_link(client, callback_query):
    file_id = int(callback_query.data.split("_")[1])
    file_doc = files_col.find_one({"file_id": file_id})
    if not file_doc:
        await callback_query.message.edit_text("❌ File not found!")
        return

    file_name = file_doc["file_name"]
    file_link = f"https://t.me/Madara_FSBot?start=file_{file_id}"

    await callback_query.message.edit_text(
        f"✅ File saved!\n\n📂 File Name: {escape_markdown(file_name)}\n\n🔗 Unique Shareable Link:\n{file_link}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Open File", url=file_link)]]),
        parse_mode=ParseMode.MARKDOWN
    )

# ---------------- AUTO DELETE ----------------
async def auto_delete_file(chat_id, msg_id, file_id):
    await asyncio.sleep(600)  # 10 minutes
    try:
        await app.delete_messages(chat_id, [msg_id])
        files_col.update_one({"file_id": file_id}, {"$set": {"status": "deleted"}})
        await app.send_message(chat_id, "⚠️ File auto-removed after 10 minutes for security.")
    except:
        pass

# ---------------- RUN BOT ----------------
print("🔥 File Sharing Bot running...")
app.run()
