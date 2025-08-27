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
import traceback

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

# ---------------- SANITIZE FILENAME ----------------
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

# ---------------- SAFE PROGRESS CALLBACK ----------------
def progress_callback(status_message, prefix=""):
    last_update = 0
    lock = asyncio.Lock()

    def callback(current, total):
        nonlocal last_update
        now = time.time()
        if now - last_update < 3:  # update every 3 seconds
            return
        last_update = now

        done = int(20 * current / total) if total else 0
        remaining = 20 - done
        percent = (current / total * 100) if total else 0
        text = f"{prefix} [{'▓'*done}{'░'*remaining}] {percent:.2f}%"

        # thread-safe edit
        async def edit():
            async with lock:
                try:
                    await status_message.edit_text(text)
                except:
                    pass

        asyncio.run_coroutine_threadsafe(edit(), app.loop)

    return callback

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
                    f"⚡ 𝗝𝗼𝗶𝗻 𝗼𝘂𝗿 𝗦𝘂𝗽𝗽𝗼𝗿𝘁 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 ⚡\n\n"
                    f"🔒 𝗔𝗰𝗰𝗲𝘀𝘀 𝗶𝘀 𝗟𝗼𝗰𝗸𝗲𝗱, 𝗼𝗻𝗹𝘆 𝗠𝗲𝗺𝗯𝗲𝗿𝘀 𝗼𝗳 𝗠𝗮𝗱𝗮𝗿𝗮 𝗙𝗮𝗺𝗶𝗹𝘆 𝗰𝗮𝗻 𝘂𝘀𝗲 ❤️🥷",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚪 Join Now", url=SUPPORT_LINK)]])
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
            "⚡ 𝗝𝗼𝗶𝗻 𝗼𝘂𝗿 𝗦𝘂𝗽𝗽𝗼𝗿𝘁 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 ⚡\n\n"
            "🔒 𝗬𝗼𝘂𝗿 𝗮𝗰𝗰𝗲𝘀𝘀 𝗶𝘀 𝗟𝗼𝗰𝗸𝗲𝗱, 𝗝𝗼𝗶𝗻 𝗳𝗶𝗿𝘀𝘁 𝘁𝗼 𝘂𝗻𝗹𝗼𝗰𝗸 ❤️🥷",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚪 Join Channel", url=SUPPORT_LINK)],
                [InlineKeyboardButton("✅ Verify Now", callback_data="verify_sub")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    await message.reply_text(
        f"👑 𝗠𝗮𝗱𝗮𝗿𝗮 𝗪𝗲𝗹𝗰𝗼𝗺𝗲𝘀 𝗬𝗼𝘂 👑\n\n"
        f"✨ 𝗛𝗲𝗹𝗹𝗼 {escape_markdown(message.from_user.first_name)} ❤️\n\n"
        f"📂 𝗦𝗲𝗻𝗱 𝗺𝗲 𝗮𝗻𝘆 𝗳𝗶𝗹𝗲 & 𝗜’𝗹𝗹 𝗰𝗿𝗲𝗮𝘁𝗲 𝗮 𝘀𝗵𝗮𝗿𝗲𝗮𝗯𝗹𝗲 𝗹𝗶𝗻𝗸 𝗳𝗼𝗿 𝘆𝗼𝘂 ⚡",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 Owner", url=f"https://t.me/{OWNER_USERNAME}"),
             InlineKeyboardButton("📢 Support", url=SUPPORT_LINK)]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

# ---------------- VERIFY ----------------
@app.on_callback_query(filters.regex("verify_sub"))
async def verify_subscription(client, callback_query):
    user_id = callback_query.from_user.id
    if await is_subscribed(user_id):
        await callback_query.message.edit_text("✅ Verified! Welcome to Madara Family ❤️")
    else:
        await callback_query.answer("❌ Not subscribed yet! Join first ⚡", show_alert=True)

# ---------------- FILE HANDLER ----------------
@app.on_message(filters.document | filters.video | filters.audio)
async def handle_file(client, message):
    if not await is_subscribed(message.from_user.id):
        await message.reply_text(
            f"⚡ 𝗝𝗼𝗶𝗻 𝗼𝘂𝗿 𝗦𝘂𝗽𝗽𝗼𝗿𝘁 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 ⚡\n\n"
            f"🔒 𝗔𝗰𝗰𝗲𝘀𝘀 𝗶𝘀 𝗟𝗼𝗰𝗸𝗲𝗱, 𝗼𝗻𝗹𝘆 𝗠𝗲𝗺𝗯𝗲𝗿𝘀 𝗼𝗳 𝗠𝗮𝗱𝗮𝗿𝗮 𝗙𝗮𝗺𝗶𝗹𝘆 𝗰𝗮𝗻 𝘂𝘀𝗲 ❤️🥷",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚪 Join Now", url=SUPPORT_LINK)]])
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
            [InlineKeyboardButton("📢 Support Channel", url=SUPPORT_LINK)]
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
        f"✏️ Send me the new file name.\n\nUse plain text or /rename [NewFileName].\n"
        f"_Tip: If you omit the extension, I keep the original._",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Support Channel", url=SUPPORT_LINK)]]),
        parse_mode=ParseMode.MARKDOWN
    )

# ---------------- SET THUMB ----------------
@app.on_message(filters.command("set_thumb") & filters.reply)
async def set_thumb(client, message):
    if not message.reply_to_message.photo:
        await message.reply_text("⚠️ Reply to an image with /set_thumb to save thumbnail.")
        return

    photo = message.reply_to_message.photo
    file_path = await app.download_media(photo, file_name=f"/tmp/thumb_{message.from_user.id}.jpg")

    users_col.update_one(
        {"user_id": message.from_user.id},
        {"$set": {"thumbnail": file_path}},
        upsert=True
    )

    await message.reply_text("✅ Successfully saved your thumbnail ❤️")

# ---------------- DELETE THUMB ----------------
@app.on_message(filters.command("del_thumb"))
async def del_thumb(client, message):
    user_doc = users_col.find_one({"user_id": message.from_user.id})
    if not user_doc or "thumbnail" not in user_doc:
        await message.reply_text("⚠️ You don’t have any thumbnail saved.")
        return

    # remove from DB
    users_col.update_one({"user_id": message.from_user.id}, {"$unset": {"thumbnail": ""}})
    # also remove local file
    try:
        if os.path.exists(user_doc["thumbnail"]):
            os.remove(user_doc["thumbnail"])
    except:
        pass

    await message.reply_text("✅ Thumbnail deleted successfully ❌")

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

    os.makedirs("/tmp/downloads", exist_ok=True)
    status_msg = await message.reply_text("📥 Downloading file...")

    try:
        orig_msg = await app.get_messages(file_doc["chat_id"], file_doc["file_id"])
        temp_file = await app.download_media(
            orig_msg,
            file_name=f"/tmp/downloads/{new_name}",
            progress=progress_callback(status_msg, prefix="📥 Downloading:")
        )

        if not temp_file:
            await status_msg.edit_text("❌ Download failed. Possibly file too large or missing.")
            return

        await status_msg.edit_text("📤 Uploading file...")

        # attach thumbnail if exists
        thumb_path = user_doc.get("thumbnail")
        sent_msg = await app.send_document(
            DATABASE_CHANNEL,
            temp_file,
            file_name=new_name,
            thumb=thumb_path if thumb_path else None,
            progress=progress_callback(status_msg, prefix="📤 Uploading:")
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")
        return

    files_col.update_one(
        {"file_id": file_id},
        {"$set": {"file_id": sent_msg.id, "chat_id": DATABASE_CHANNEL, "file_name": new_name}}
    )
    file_link = f"https://t.me/Madara_FSBot?start=file_{sent_msg.id}"

    await status_msg.edit_text(
        f"✅ **File renamed & saved!**\n\n📂 {escape_markdown(new_name)}\n\n🔗 Shareable Link:\n{file_link}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗃️ Open File", url=file_link)],
            [InlineKeyboardButton("📢 Support Channel", url=SUPPORT_LINK)]
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

@app.on_message(filters.text & ~filters.command(["start","rename","set_thumb","del_thumb","broadcast"]))
async def rename_text(client, message):
    user_doc = users_col.find_one({"user_id": message.from_user.id})
    if user_doc and "renaming_file_id" in user_doc:
        await perform_rename(message.from_user.id, message.text.strip(), message)

# ---------------- BROADCAST ----------------
@app.on_message(filters.command("broadcast") & filters.user(OWNER_IDS))
async def broadcast_handler(client, message):
    # Determine broadcast content
    if message.reply_to_message:
        b_msg = message.reply_to_message
    elif len(message.command) > 1:
        b_msg = message.text.split(maxsplit=1)[1]
    else:
        await message.reply_text("⚠️ Usage:\nReply to a message with /broadcast\nOr use: /broadcast Your text")
        return

    sent, failed = 0, 0
    users = users_col.find({})
    total = users_col.count_documents({})
    status = await message.reply_text(f"📢 Broadcasting started...\n👥 Total Users: {total}")

    for user in users:
        try:
            uid = user["user_id"]

            # Media broadcast
            if hasattr(b_msg, "photo") and b_msg.photo:
                await app.send_photo(uid, b_msg.photo.file_id, caption=b_msg.caption or "")
            elif hasattr(b_msg, "video") and b_msg.video:
                await app.send_video(uid, b_msg.video.file_id, caption=b_msg.caption or "")
            elif hasattr(b_msg, "document") and b_msg.document:
                await app.send_document(uid, b_msg.document.file_id, caption=b_msg.caption or "")
            # Text broadcast
            elif isinstance(b_msg, str):
                await app.send_message(uid, b_msg)
            else:
                continue

            sent += 1
            await asyncio.sleep(0.2)  # small delay to avoid FloodWait

        except Exception:
            failed += 1
            continue

    await status.edit_text(
        f"✅ Broadcast completed!\n\n"
        f"👥 Total Users: {total}\n"
        f"📩 Sent: {sent}\n"
        f"⚠️ Failed: {failed}"
    )


# ---------------- RUN BOT ----------------
print("🔥 Madara File Sharing Bot running safely on Heroku...")
app.run()
