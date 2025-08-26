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
async def is_subscribed(user_id):
    try:
        member = await app.get_chat_member(FORCE_SUBSCRIBE_CHANNEL, user_id)
        return member.status not in ["left", "kicked"]
    except:
        return False

# ---------------- CONTENT RESTRICT CHECK ----------------
def is_restricted(file_name):
    restricted_keywords = ["porn", "xxx", "adult", "18+"]  # extendable
    return any(word in file_name.lower() for word in restricted_keywords)

# ---------------- START COMMAND ----------------
@app.on_message(filters.command("start"))
async def start(client, message):
    # Store user info for broadcasts
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

    # Normal start message with Owner, Support, Premium, and Help buttons
    await message.reply_text(
        f"👋 Hello {message.from_user.first_name}!\n\n"
        "Forward any file to me and I will generate a **permanent Telegram shareable link**!\n\n"
        "⚡ Premium: links never expire.\n"
        "📌 Stay subscribed for updates and uninterrupted service.\n\n"
        "ℹ️ Need help? Click Help below.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Owner", url=f"https://t.me/{OWNER_USERNAME}"),
             InlineKeyboardButton("Support Channel", url=SUPPORT_LINK)],
            [InlineKeyboardButton("Premium Access 💎", url=SUPPORT_LINK),
             InlineKeyboardButton("Help ❓", callback_data="help")]
        ])
    )

# ---------------- VERIFY SUB BUTTON ----------------
@app.on_callback_query(filters.regex("verify_sub"))
async def verify_subscription(client, callback_query):
    user_id = callback_query.from_user.id
    if await is_subscribed(user_id):
        await callback_query.message.edit_text(
            f"✅ Verification successful!\n\n"
            "You can now forward any file to receive a permanent shareable Telegram link.",
            reply_markup=None
        )
    else:
        await callback_query.answer(
            "❌ You are not yet subscribed! Please join the channel first.",
            show_alert=True
        )

# ---------------- HELP BUTTON ----------------
@app.on_callback_query(filters.regex("help"))
async def help_button(client, callback_query):
    await callback_query.message.edit_text(
        "ℹ️ **Bot Usage Help**\n\n"
        "1. Forward any document, video, or audio to the bot.\n"
        "2. The bot will give you a **permanent Telegram link**.\n"
        "3. Links are protected (no forwarding / screenshot).\n"
        "4. Files auto-delete from your chat after 10 minutes.\n"
        "5. Use /get <message_id> to fetch a file by its ID.\n"
        "6. Only adult/copyright-free content allowed.\n\n"
        "⚡ Premium users enjoy never-expiring links.\n"
        "📌 Keep subscribed to our support channel for updates.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Back to Start", callback_data="back_start")]
        ])
    )

# ---------------- BACK TO START BUTTON ----------------
@app.on_callback_query(filters.regex("back_start"))
async def back_to_start(client, callback_query):
    await start(client, callback_query.message)

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
    file_name = message.document.file_name if message.document else message.video.file_name if message.video else message.audio.file_name

    # Polite adult content restriction
    if is_restricted(file_name):
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
        "file_id": fwd_msg.message_id,
        "chat_id": fwd_msg.chat.id,
        "user_id": message.from_user.id,
        "file_name": file_name,
        "timestamp": datetime.datetime.utcnow(),
        "status": "active"
    }
    files_col.insert_one(file_record)

    # Generate permanent shareable link (fast/direct download simulation)
    file_link = f"{WEB_URL}/file/{fwd_msg.message_id}"

    # Send message with protect_content to prevent forwarding / screenshot
    sent_msg = await message.reply_text(
        f"✅ File uploaded successfully!\n\nYour permanent shareable link:\n{file_link}",
        disable_web_page_preview=True,
        protect_content=True,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Open File Link", url=file_link)]])
    )

    # Auto-delete user DM after 10 minutes
    await asyncio.sleep(600)
    try:
        await client.delete_messages(message.chat.id, message.message_id)
        await client.delete_messages(message.chat.id, sent_msg.message_id)
        files_col.update_one({"file_id": fwd_msg.message_id}, {"$set": {"status": "deleted"}})
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
                message_ids=file_doc["file_id"],
                protect_content=True
            )
        else:
            await message.reply_text("❌ File not found or deleted!")
    except:
        await message.reply_text("Usage: /get <message_id>")

# ---------------- OWNER BROADCAST ----------------
@app.on_message(filters.command("broadcast") & filters.user(OWNER_IDS))
async def broadcast(client, message):
    text_to_send = message.text.split(maxsplit=1)
    if len(text_to_send) < 2:
        await message.reply_text("Usage: /broadcast <text or link or file>")
        return
    text_to_send = text_to_send[1]

    users = users_col.find({})
    count = 0
    for user in users:
        try:
            await client.send_message(user["user_id"], f"📢 Broadcast Message:\n\n{text_to_send}", protect_content=True)
            count += 1
        except:
            continue
    await message.reply_text(f"✅ Broadcast sent to {count} users!")

# ---------------- RUN BOT ----------------
print("🔥 Advanced File to Link Bot is running...")
app.run()
