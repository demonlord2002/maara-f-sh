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

# ---------------- CANCEL FLAGS ----------------
cancel_flags = {}  # user_id: True/False

# ---------------- PROGRESS FUNCTION ----------------
async def progress(current, total, message, prefix="", user_id=None):
    if user_id and cancel_flags.get(user_id):
        raise asyncio.CancelledError()
    try:
        percent = current * 100 / total
        await message.edit_text(
            f"{prefix} {percent:.1f}% ({current/1024:.1f}KB/{total/1024:.1f}KB)",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_progress")]
            ])
        )
    except:
        pass

# ---------------- CANCEL BUTTON CALLBACK ----------------
@app.on_callback_query(filters.regex("cancel_progress"))
async def cancel_progress_cb(client, callback_query):
    cancel_flags[callback_query.from_user.id] = True
    await callback_query.answer("⏹️ Operation cancelled!", show_alert=True)

# ---------------- START COMMAND ----------------
@app.on_message(filters.command("start"))
async def start(client, message):
    args = message.text.split(maxsplit=1)

    # If user opened via file link
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

    # Save/update user info
    users_col.update_one(
        {"user_id": message.from_user.id},
        {"$set": {
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name
        }},
        upsert=True
    )

    # Subscription check
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
    example = "www.1TamilMV.blue - Kingdom (2025) Tamil HQ HDRip - x264 - AAC - 400MB - ESub.mkv"
    await callback_query.message.edit_text(
        "✏️ Send me the **new file name**.\n\n"
        "You can reply with plain text **or** use the command:\n"
        f"`/rename {example}`\n\n"
        "_Tip: If you omit the extension, I'll keep the original one._",
        parse_mode=ParseMode.MARKDOWN
    )

# ---------------- INTERNAL: DO RENAME ----------------
async def perform_rename_and_reupload(user_id: int, new_name: str, message):
    cancel_flags[user_id] = False  # reset cancel flag

    user_doc = users_col.find_one({"user_id": user_id})
    if not user_doc or "renaming_file_id" not in user_doc:
        await message.reply_text("⚠️ First send a file and tap **Yes, rename ✏️**.", parse_mode=ParseMode.MARKDOWN)
        return

    file_id = user_doc["renaming_file_id"]
    file_doc = files_col.find_one({"file_id": file_id})
    if not file_doc:
        await message.reply_text("❌ Original file not found!")
        return

    orig_ext = os.path.splitext(file_doc["file_name"])[1]
    if not new_name.endswith(orig_ext):
        new_name = f"{new_name}{orig_ext}"

    os.makedirs("downloads", exist_ok=True)

    try:
        orig_msg = await app.get_messages(file_doc["chat_id"], file_doc["file_id"])
        temp_file = await app.download_media(
            message=orig_msg,
            file_name=f"downloads/{new_name}",
            progress=lambda c, t: asyncio.get_event_loop().create_task(
                progress(c, t, message, "Downloading:", user_id)
            )
        )
        if not temp_file or not os.path.exists(temp_file):
            await message.reply_text("❌ Download failed. Please try again.")
            return
    except asyncio.CancelledError:
        await message.reply_text("❌ Download cancelled by user.")
        return
    except Exception as e:
        await message.reply_text(f"❌ Download error: `{str(e)}`", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        if temp_file.endswith((".mp4", ".mkv", ".mov")):
            sent_msg = await app.send_video(
                DATABASE_CHANNEL, temp_file, file_name=new_name,
                progress=lambda c, t: asyncio.get_event_loop().create_task(
                    progress(c, t, message, "Uploading:", user_id)
                )
            )
        elif temp_file.endswith((".mp3", ".m4a", ".wav")):
            sent_msg = await app.send_audio(
                DATABASE_CHANNEL, temp_file, file_name=new_name,
                progress=lambda c, t: asyncio.get_event_loop().create_task(
                    progress(c, t, message, "Uploading:", user_id)
                )
            )
        else:
            sent_msg = await app.send_document(
                DATABASE_CHANNEL, temp_file, file_name=new_name,
                progress=lambda c, t: asyncio.get_event_loop().create_task(
                    progress(c, t, message, "Uploading:", user_id)
                )
            )
    except asyncio.CancelledError:
        await message.reply_text("❌ Upload cancelled by user.")
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return
    except Exception as e:
        await message.reply_text(f"❌ Upload failed: `{str(e)}`", parse_mode=ParseMode.MARKDOWN)
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return

    files_col.update_one(
        {"file_id": file_id},
        {"$set": {
            "file_id": sent_msg.id,
            "chat_id": DATABASE_CHANNEL,
            "file_name": new_name,
            "status": "active"
        }}
    )

    file_link = f"https://t.me/Madara_FSBot?start=file_{sent_msg.id}"

    await message.reply_text(
        f"✅ **File renamed & saved!**\n\n"
        f"📂 New Name: `{escape_markdown(new_name)}`\n\n"
        f"🔗 Link: {file_link}\n\n"
        f"⚠️ This file auto-deletes after 10 minutes.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Open File", url=file_link)]]),
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        os.remove(temp_file)
    except:
        pass

    users_col.update_one({"user_id": user_id}, {"$unset": {"renaming_file_id": ""}})
    cancel_flags[user_id] = False

# ---------------- /rename COMMAND ----------------
@app.on_message(filters.command("rename"))
async def rename_command(client, message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        example = "www.1TamilMV.blue - Kingdom (2025) Tamil HQ HDRip - x264 - AAC - 400MB - ESub.mkv"
        await message.reply_text(f"Usage:\n`/rename {example}`", parse_mode=ParseMode.MARKDOWN)
        return
    new_name = parts[1].strip()
    await perform_rename_and_reupload(message.from_user.id, new_name, message)

# ---------------- PLAIN TEXT RENAME ----------------
@app.on_message(filters.text & ~filters.command(["start", "rename"]))
async def handle_rename_text(client, message):
    user_doc = users_col.find_one({"user_id": message.from_user.id})
    if not user_doc or "renaming_file_id" not in user_doc:
        return
    new_name = message.text.strip()
    await perform_rename_and_reupload(message.from_user.id, new_name, message)

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
        f"✅ **File saved!**\n\n"
        f"📂 File Name: - {escape_markdown(file_name)}\n\n"
        f"🔗 Unique Shareable Link:\n{file_link}\n\n"
        f"⚠️ Note: This link is temporary. File will be automatically removed after 10 minutes for security reasons.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Open File", url=file_link)]]),
        parse_mode=ParseMode.MARKDOWN
    )

# ---------------- AUTO DELETE ----------------
async def auto_delete_file(chat_id, msg_id, file_id):
    await asyncio.sleep(600)
    try:
        await app.delete_messages(chat_id, [msg_id])
        files_col.update_one({"file_id": file_id}, {"$set": {"status": "deleted"}})
        await app.send_message(chat_id, "⚠️ File auto-removed after 10 minutes for security.")
    except:
        pass

# ---------------- RUN BOT ----------------
print("🔥 File Sharing Bot running...")
app.run()
