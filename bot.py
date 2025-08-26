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

# ---------------- CONTENT RESTRICT CHECK ----------------
def is_restricted(file_name: str) -> bool:
    restricted_keywords = ["porn", "xxx", "adult", "18+"]  # extendable
    return any(word in file_name.lower() for word in restricted_keywords)

# ---------------- START COMMAND ----------------
@app.on_message(filters.command("start"))
async def start(client, message):
    # store user info for broadcasts
    users_col.update_one(
        {"user_id": message.from_user.id},
        {"$set": {
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name
        }},
        upsert=True
    )

    # Force subscribe check
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

    # Normal start message
    await message.reply_text(
        f"👋 Hello {message.from_user.first_name}!\n\n"
        "Forward any file to me and I will instantly generate a **permanent Telegram shareable link**!\n\n"
        "⚡ Premium: links never expire.\n"
        "📌 Stay subscribed to our channel for updates and uninterrupted service.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Owner", url=f"https://t.me/{OWNER_USERNAME}"),
             InlineKeyboardButton("Support Channel", url=SUPPORT_LINK)],
            [InlineKeyboardButton("Premium Access 💎", url=SUPPORT_LINK)]
        ])
    )

# ---------------- VERIFY SUB BUTTON ----------------
@app.on_callback_query(filters.regex("verify_sub"))
async def verify_subscription(client, callback_query):
    user_id = callback_query.from_user.id
    if await is_subscribed(user_id):
        await callback_query.message.edit_text(
            f"✅ Verification successful!\n\n"
            "You can now forward any file to receive a permanent shareable Telegram link."
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

    # Determine file name
    file_name = None
    if message.document:
        file_name = message.document.file_name
    elif message.video:
        file_name = message.video.file_name
    elif message.audio:
        file_name = message.audio.file_name

    # Polite adult content restriction
    if file_name and is_restricted(file_name):
        await message.reply_text(
            "⚠️ Oops! This file type is restricted.\n"
            "Please avoid sending adult or copyrighted content.\n"
            "Your cooperation keeps this bot safe and available for everyone. 🙏"
        )
        return

    # Forward file to database channel
    fwd_msg = await message.forward(DATABASE_CHANNEL)

    # Save file info in MongoDB
    file_record = {
        "file_id": fwd_msg.id,  # ✅ updated for Pyrogram v2
        "chat_id": fwd_msg.chat.id,
        "user_id": message.from_user.id,
        "file_name": file_name,
        "timestamp": datetime.datetime.utcnow(),
        "status": "active"
    }
    files_col.insert_one(file_record)

    # Generate permanent Telegram link
    file_link = f"https://t.me/{DATABASE_CHANNEL.strip('@')}/{fwd_msg.id}"
    
    # Send file info
    sent_msg = await message.reply_text(
        f"✅ File uploaded successfully!\n\nYour permanent Telegram link:\n{file_link}",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Open File Link", url=file_link)]])
    )

    # ---------------- AUTO DELETE USER DM AFTER 10 MINUTES ----------------
    await asyncio.sleep(600)  # 10 minutes
    try:
        await client.delete_messages(message.chat.id, [message.id, sent_msg.id])
        files_col.update_one({"file_id": fwd_msg.id}, {"$set": {"status": "deleted"}})
    except:
        pass

# ---------------- GET FILE BY LINK ----------------
@app.on_message(filters.command("get"))
async def send_file(client, message):
    try:
        msg_id = int(message.text.split()[1])
        file_doc = files_col.find_one({"file_id": msg_id, "status": "active"})
        if file_doc:
            await client.forward_messages(
                message.chat.id,
                chat_id=file_doc["chat_id"],
                message_ids=file_doc["file_id"]
            )
        else:
            await message.reply_text("❌ File not found or deleted!")
    except:
        await message.reply_text("Usage: /get <message_id>")

# ---------------- OWNER BROADCAST ----------------
@app.on_message(filters.command("broadcast") & filters.user(OWNER_IDS))
async def broadcast(client, message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text("Usage: /broadcast <text>")
        return

    text_to_send = parts[1]
    users = users_col.find({})
    count = 0
    for user in users:
        try:
            await client.send_message(user["user_id"], f"📢 Broadcast Message:\n\n{text_to_send}")
            count += 1
        except:
            continue
    await message.reply_text(f"✅ Broadcast sent to {count} users!")

# ---------------- RUN BOT ----------------
print("🔥 Advanced File to Link Bot is running...")
app.run()
