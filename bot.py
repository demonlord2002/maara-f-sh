from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from config import *
import datetime
import asyncio

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

# ---------------- START COMMAND ----------------
@app.on_message(filters.command("start"))
async def start(client, message):
    # Check if it's a file start link
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith("file_"):
        file_id = int(args[1].replace("file_", ""))
        file_doc = files_col.find_one({"file_id": file_id, "status": "active"})
        if file_doc:
            await client.forward_messages(
                message.chat.id,
                chat_id=file_doc["chat_id"],
                message_ids=file_doc["file_id"]
            )
            return
        else:
            await message.reply_text("❌ This file is not available anymore.")
            return

    # Otherwise normal start
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
            f"🚨 Access Restricted!\n\nTo use this bot, you must join our official channel first.\n"
            "After joining, press **Verify** to continue.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel ✅", url=SUPPORT_LINK)],
                [InlineKeyboardButton("✅ Verify Joined", callback_data="verify_sub")]
            ])
        )
        return

    await message.reply_text(
        f"👋 Hello {message.from_user.first_name}!\n\n"
        "Send me any file and I will give you a **shareable link**.\n\n"
        "When your friends click that link, the bot will deliver the file to them instantly 🚀",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Owner", url=f"https://t.me/{OWNER_USERNAME}"),
             InlineKeyboardButton("Support Channel", url=SUPPORT_LINK)]
        ])
    )

# ---------------- VERIFY SUB BUTTON ----------------
@app.on_callback_query(filters.regex("verify_sub"))
async def verify_subscription(client, callback_query):
    user_id = callback_query.from_user.id
    if await is_subscribed(user_id):
        await callback_query.message.edit_text(
            f"✅ Verification successful!\n\n"
            "Now send me a file to get a permanent shareable link."
        )
    else:
        await callback_query.answer(
            "❌ You are not yet subscribed! Please join the channel first.",
            show_alert=True
        )

# ---------------- FILE HANDLER ----------------
@app.on_message(filters.document | filters.video | filters.audio)
async def handle_file(client, message):
    if not await is_subscribed(message.from_user.id):
        await message.reply_text(
            f"🚨 You must join our channel to use this bot!\n\n👉 {SUPPORT_LINK}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel ✅", url=SUPPORT_LINK)]])
        )
        return

    # Get file info
    file_name = None
    if message.document:
        file_name = message.document.file_name
    elif message.video:
        file_name = message.video.file_name
    elif message.audio:
        file_name = message.audio.file_name

    # Forward file to database channel
    fwd_msg = await message.forward(DATABASE_CHANNEL)

    # Save file info
    file_record = {
        "file_id": fwd_msg.id,
        "chat_id": fwd_msg.chat.id,
        "user_id": message.from_user.id,
        "file_name": file_name,
        "timestamp": datetime.datetime.now(datetime.UTC),  # ✅ fixed
        "status": "active"
    }
    files_col.insert_one(file_record)

    # Generate shareable start link
    file_link = f"https://t.me/{BOT_USERNAME}?start=file_{fwd_msg.id}"

    await message.reply_text(
        f"✅ File saved!\n\n"
        f"📂 **File Name:** `{file_name}`\n\n"
        f"🔗 **Shareable Link:**\n{file_link}\n\n"
        f"Anyone who clicks this link will get the file instantly from me 🤖",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Open File", url=file_link)]])
    )

# ---------------- RUN BOT ----------------
print("🔥 File Sharing Bot is running...")
app.run()
