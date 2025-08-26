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
    args = message.text.split(maxsplit=1)

    # If user clicks a file link
    if len(args) > 1 and args[1].startswith("file_"):
        file_id = int(args[1].replace("file_", ""))
        file_doc = files_col.find_one({"file_id": file_id, "status": "active"})
        if file_doc:
            if not await is_subscribed(message.from_user.id):
                await message.reply_text(
                    f"🚨 To access this file, you must first join our official channel!\n"
                    f"👉 {SUPPORT_LINK}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel ✅", url=SUPPORT_LINK)]])
                )
                return

            # Copy the file instead of forwarding
            sent_msg = await app.copy_message(
                chat_id=message.chat.id,
                from_chat_id=file_doc["chat_id"],
                message_id=file_doc["file_id"]
            )

            # Auto-delete after 10 minutes
            asyncio.create_task(auto_delete_file(message.chat.id, sent_msg.id, file_id))
            return
        else:
            await message.reply_text("❌ Sorry! This file is no longer available.")
            return

    # Normal start (not a file link)
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
            f"🚨 Access Restricted!\n\nYou must join our official channel to use this bot.\n"
            "Press **Verify** after joining.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel ✅", url=SUPPORT_LINK)],
                [InlineKeyboardButton("✅ Verify Joined", callback_data="verify_sub")]
            ])
        )
        return

    await message.reply_text(
        f"👋 Hello {message.from_user.first_name}!\n\n"
        "Send me any file and I will create a **unique, safe, shareable link** for you.\n"
        "Your friends will receive the file directly from the bot when they click the link 🚀",
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
            f"✅ Verification successful!\n\nYou can now send files and get instant safe shareable links."
        )
    else:
        await callback_query.answer(
            "❌ You are not subscribed yet! Please join the channel first.",
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
    file_name = message.document.file_name if message.document else \
                message.video.file_name if message.video else \
                message.audio.file_name

    # Copy the file to DB channel
    fwd_msg = await app.copy_message(DATABASE_CHANNEL, message.chat.id, message.id)

    # Save file info
    file_record = {
        "file_id": fwd_msg.id,
        "chat_id": fwd_msg.chat.id,
        "user_id": message.from_user.id,
        "file_name": file_name,
        "timestamp": datetime.datetime.now(datetime.timezone.utc),
        "status": "active"
    }
    files_col.insert_one(file_record)

    # Generate safe shareable link
    file_link = f"https://t.me/Madara_FSBot?start=file_{fwd_msg.id}"

    await message.reply_text(
        f"✅ File saved!\n\n"
        f"📂 **File Name:** `{file_name}`\n\n"
        f"🔗 **Unique Shareable Link:**\n{file_link}\n\n"
        f"⚠️ Note: This link is temporary. File will be automatically removed after 10 minutes for security reasons.",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Open File", url=file_link)]])
    )

    # Schedule auto-delete
    asyncio.create_task(auto_delete_file(message.chat.id, fwd_msg.id, fwd_msg.id))

# ---------------- AUTO DELETE FUNCTION ----------------
async def auto_delete_file(chat_id, msg_id, file_id):
    await asyncio.sleep(600)  # 10 minutes
    try:
        await app.delete_messages(chat_id, [msg_id])
        files_col.update_one({"file_id": file_id}, {"$set": {"status": "deleted"}})
        await app.send_message(
            chat_id,
            "⚠️ The file has been automatically removed after 10 minutes due to copyright/security rules. "
            "We protect all users and content. 🛡️"
        )
    except:
        pass

# ---------------- RUN BOT ----------------
print("🔥 File Sharing Bot is running...")
app.run()
