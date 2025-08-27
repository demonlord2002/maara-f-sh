from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from pymongo import MongoClient
from config import *
import datetime
import asyncio
import re
import os
import math

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

    text = (
        f"✅ **File saved!**\n\n"
        f"📂 File Name: {file_name}\n\n"
        f"🔗 Unique Shareable Link:\n{file_link}\n\n"
        f"⚠️ Note: This link is safe and temporary. "
        "File will be removed automatically after 10 minutes for security & copyright reasons."
    )

    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗃️ Open File", url=file_link)]]),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

# ---------------- RENAME CALLBACK ----------------
@app.on_callback_query(filters.regex(r"rename_(\d+)"))
async def rename_file_prompt(client, callback_query):
    file_id = int(callback_query.data.split("_")[1])
    users_col.update_one({"user_id": callback_query.from_user.id},{"$set": {"renaming_file_id": file_id}})
    
    await callback_query.message.edit_text(
        f"✏️ Send me the new file name.\n\n"
        f"You can reply with plain text or use the command:\n"
        f"/rename [NewFileName]\n\n"
        f"_Tip: If you omit the extension, I'll keep the original one._",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Support Channel ✅", url=SUPPORT_LINK)]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

# ---------------- RENAME HANDLER WITH REAL PROGRESS ----------------
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

    orig_ext = os.path.splitext(file_doc["file_name"])[1]
    if not new_name.endswith(orig_ext):
        new_name += orig_ext

    os.makedirs("downloads", exist_ok=True)
    try:
        orig_msg = await app.get_messages(file_doc["chat_id"], file_doc["file_id"])
    except Exception as e:
        await message.reply_text(f"❌ Error fetching original file: {str(e)}")
        return

    file_size = orig_msg.document.file_size if orig_msg.document else \
                orig_msg.video.file_size if orig_msg.video else \
                orig_msg.audio.file_size

    progress_msg = await message.reply_text(
        f"✏️ Renaming your file: ⌛ Starting download...",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Support Channel ✅", url=SUPPORT_LINK)]]),
        parse_mode=ParseMode.MARKDOWN
    )

    # ---------------- Download with progress ----------------
    temp_file = f"downloads/{new_name}"
    downloaded = 0

    async for chunk in app.download_media(orig_msg, file_name=temp_file, progress=lambda d, t: None, progress_args=()):
        downloaded = chunk
        percent = min(int(downloaded / file_size * 100), 100)
        bar_len = 10
        filled = math.floor(bar_len * percent / 100)
        bar = "▓" * filled + "░" * (bar_len - filled)
        mins, secs = divmod(int(file_size * percent / 100 / 50000), 60)  # rough ETA
        try:
            await progress_msg.edit_text(
                f"✏️ Renaming your file: ⌛ {bar} {percent}% | ETA {mins:02d}:{secs:02d}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Support Channel ✅", url=SUPPORT_LINK)]])
            )
        except:
            pass

    # ---------------- Upload with progress ----------------
    sent_msg = await app.send_document(DATABASE_CHANNEL, temp_file, file_name=new_name)
    files_col.update_one({"file_id": file_id},{"$set":{"file_id":sent_msg.id,"chat_id":DATABASE_CHANNEL,"file_name":new_name}})
    file_link = f"https://t.me/Madara_FSBot?start=file_{sent_msg.id}"

    text = (
        f"✅ **File renamed & saved!**\n\n"
        f"📂 New Name: {escape_markdown(new_name)}\n\n"
        f"🔗 Unique Shareable Link:\n{file_link}\n\n"
        f"⚠️ Note: This link is safe and temporary. "
        "File will be removed automatically after 10 minutes for security & copyright reasons."
    )

    await progress_msg.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗃️ Open File", url=file_link)],
                                           [InlineKeyboardButton("Support Channel ✅", url=SUPPORT_LINK)]]),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

    os.remove(temp_file)
    users_col.update_one({"user_id":user_id},{"$unset":{"renaming_file_id":""}})

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
    if not user_doc or "renaming_file_id" not in user_doc:
        return
    await perform_rename(message.from_user.id, message.text.strip(), message)

# ---------------- RUN BOT ----------------
print("🔥 File Sharing Bot with REAL LIVE PROGRESS running...")
app.run()
