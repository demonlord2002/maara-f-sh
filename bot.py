from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.enums import ParseMode
from pymongo import MongoClient
from config import *
import datetime
import asyncio
import re
import os
import traceback
import shlex
import time
import subprocess
import imageio_ffmpeg as ffmpeg

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
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!])", r"\\\1", text)

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
        if now - last_update < 3:
            return
        last_update = now

        done = int(20 * current / total) if total else 0
        remaining = 20 - done
        percent = (current / total * 100) if total else 0
        text = f"{prefix} [{'▓'*done}{'░'*remaining}] {percent:.2f}%"

        async def edit():
            async with lock:
                try:
                    await status_message.edit_text(text)
                except:
                    pass

        asyncio.run_coroutine_threadsafe(edit(), app.loop)

    return callback

# ---------------- HELPER: GET FILE DOC ----------------
def get_file_doc_by_any_id(fid, active_only=False):
    query = {"$or": [{"message_id": fid}, {"file_unique_id": fid}]}
    if active_only:
        query["status"] = "active"
    return files_col.find_one(query)

# ---------------- START COMMAND ----------------
@app.on_message(filters.command("start"))
async def start(client, message):
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith("file_"):
        file_id = int(args[1].replace("file_", ""))
        file_doc = get_file_doc_by_any_id(file_id, active_only=True)
        if file_doc:
            if not await is_subscribed(message.from_user.id):
                await message.reply_text(
                    f"⚡ 𝗝𝗼𝗶𝗻 𝗼𝘂𝗿 𝗦𝘂𝗽𝗽𝗼𝗿𝘁 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 ⚡\n\n"
                    f"🔒 𝗔𝗰𝗰𝗲𝘀𝘀 𝗶𝘀 𝗟𝗼𝗰𝗸𝗲𝗱, 𝗼𝗻𝗹𝘆 𝗠𝗲𝗺𝗯𝗲𝗿𝘀 𝗼𝗳 𝗠𝗮𝗱𝗮𝗿𝗮 𝗙𝗮𝗺𝗶𝗹𝘆 𝗰𝗮𝗻 𝘂𝘀𝗲 ❤️🥷",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("🚪 Join Now", url=SUPPORT_LINK)]]
                    )
                )
                return

            sent_msg = await app.copy_message(
                chat_id=message.chat.id,
                from_chat_id=file_doc["chat_id"],
                message_id=file_doc["message_id"]
            )

            warn_msg = await message.reply_text(
                "⚠️ **Due to copyright ©️ issues this file will be auto-deleted in 10 minutes!**\n\n"
                "💾 Save it to your **Saved Messages** immediately ⚡\n\n"
                "👑 Madara protects his Family ❤️🥷"
            )

            async def delete_later():
                await asyncio.sleep(600)
                try:
                    await sent_msg.delete()
                    await warn_msg.edit_text("❌ File deleted automatically due to copyright ©️ rules.")
                except:
                    pass

            asyncio.create_task(delete_later())
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

    # Copy message to DATABASE_CHANNEL
    fwd_msg = await app.copy_message(DATABASE_CHANNEL, message.chat.id, message.id)

    # Determine the chat_id to save: use DATABASE_CHANNEL numeric ID
    chat_id_to_save = DATABASE_CHANNEL if DATABASE_CHANNEL else fwd_msg.chat.id

    # Insert file into MongoDB
    files_col.insert_one({
        "message_id": fwd_msg.id,
        "chat_id": chat_id_to_save,
        "file_unique_id": (
            message.document.file_unique_id
            if message.document else
            message.video.file_unique_id
            if message.video else
            message.audio.file_unique_id
        ),
        "user_id": message.from_user.id,
        "file_name": file_name,
        "timestamp": datetime.datetime.now(datetime.timezone.utc),
        "status": "active"
    })

    await message.reply_text(
        f"✅ **File received!**\n\n"
        f"💡 **Do you want to rename before getting a shareable link?**\n\n"
        f"🖼️ **Use /set_thumb to set a custom thumbnail**\n"
        f"❌ **Use /del_thumb to delete your thumbnail**\n\n"
        f"Original: `{safe_file_name}`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Yes, rename ✏️", callback_data=f"rename_{fwd_msg.id}")],
            [InlineKeyboardButton("No, give link 🔗", callback_data=f"link_{fwd_msg.id}")],
            [InlineKeyboardButton("Sample video 📷", callback_data=f"sample_{fwd_msg.id}")],
            [InlineKeyboardButton("📢 Support Channel", url=SUPPORT_LINK)]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

# ---------------- SAMPLE BUTTON ----------------
@app.on_callback_query(filters.regex(r"sample_(\d+)"))
async def sample_info(client, callback_query):
    file_id = int(callback_query.data.split("_")[1])
    file_doc = get_file_doc_by_any_id(file_id)
    if not file_doc:
        return await callback_query.message.edit_text("❌ File not found!")

    await callback_query.message.edit_text(
        f"📹 To get a sample of this video, reply with the command:\n\n"
        f"`/sample HH:MM:SS to HH:MM:SS`\n\n"
        f"⏱ Duration must be 1–60 seconds.\n\n"
        f"📢 Support: {SUPPORT_LINK}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Support Channel", url=SUPPORT_LINK)]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

# ---------------- SAMPLE COMMAND ----------------
ffmpeg_path = ffmpeg.get_ffmpeg_exe()

@app.on_message(filters.command("sample"))
async def sample_trim(client, message: Message):
    # Check if message is a reply to a video/document
    if not message.reply_to_message or not (
        message.reply_to_message.video or message.reply_to_message.document
    ):
        return await message.reply("⚠️ Please reply to a video file with:\n/sample HH:MM:SS to HH:MM:SS")

    # Parse command times
    match = re.search(r"(\d{2}):(\d{2}):(\d{2})\s+to\s+(\d{2}):(\d{2}):(\d{2})", message.text)
    if not match:
        return await message.reply("❌ Invalid format. Use:\n/sample 00:10:00 to 00:10:30")

    h1, m1, s1, h2, m2, s2 = map(int, match.groups())

    # Validate seconds & minutes
    for val in [m1, s1, m2, s2]:
        if val >= 60:
            return await message.reply("⚠️ Minutes and seconds must be less than 60!")

    start_sec = h1*3600 + m1*60 + s1
    end_sec = h2*3600 + m2*60 + s2
    duration = end_sec - start_sec

    if duration <= 0 or duration > 60:
        return await message.reply("⚠️ Duration must be between 1–60 seconds.")

    msg = await message.reply("📥 Downloading video...")

    try:
        input_path = await message.reply_to_message.download()
    except Exception:
        return await msg.edit("❌ Download failed. File not saved properly.")

    output_path = f"/tmp/sample_clip_{message.from_user.id}.mp4"
    await msg.edit("✂️ Trimming sample video...")

    # FFmpeg command using imageio-ffmpeg executable
    ffmpeg_cmd = [
        ffmpeg_path,
        "-i", input_path,
        "-ss", str(start_sec),
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", "128k",
        "-y",
        output_path
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
    except Exception as e:
        os.remove(input_path)
        return await msg.edit(f"❌ FFmpeg execution failed:\n{e}")

    # Check output validity
    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        os.remove(input_path)
        return await msg.edit(f"❌ Failed to generate sample. FFmpeg error:\n{stderr.decode()}")

    await msg.edit("📤 Uploading sample...")

    await client.send_video(
        chat_id=message.chat.id,
        video=output_path,
        caption=f"✂️ Sample clip from {h1:02}:{m1:02}:{s1:02} to {h2:02}:{m2:02}:{s2:02}"
    )

    # Cleanup
    os.remove(input_path)
    os.remove(output_path)
    await msg.delete()

# ---------------- LINK CALLBACK ----------------
@app.on_callback_query(filters.regex(r"link_(\d+)"))
async def send_shareable_link(client, callback_query):
    file_id = int(callback_query.data.split("_")[1])
    file_doc = get_file_doc_by_any_id(file_id)
    if not file_doc:
        await callback_query.message.edit_text("❌ File not found!")
        return

    file_name = escape_markdown(file_doc["file_name"])
    file_link = f"https://t.me/Madara_FSBot?start=file_{file_doc['message_id']}"

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

    orig_file_id = user_doc["renaming_file_id"]
    orig_doc = get_file_doc_by_any_id(orig_file_id)
    if not orig_doc:
        await message.reply_text("❌ Original file not found!")
        return

    # Sanitize new filename
    new_name = sanitize_filename(new_name)
    orig_ext = os.path.splitext(orig_doc["file_name"])[1]
    if not new_name.endswith(orig_ext):
        new_name += orig_ext

    os.makedirs("/tmp/downloads", exist_ok=True)
    status_msg = await message.reply_text("📥 Downloading original file...")

    try:
        orig_msg = await app.get_messages(orig_doc["chat_id"], orig_doc["message_id"])
        temp_file = await app.download_media(
            orig_msg,
            file_name=f"/tmp/downloads/{new_name}",
            progress=progress_callback(status_msg, prefix="📥 Downloading:")
        )

        if not temp_file:
            await status_msg.edit_text("❌ Download failed.")
            return

        await status_msg.edit_text("📤 Uploading renamed file...")

        thumb_path = user_doc.get("thumbnail")
        sent_msg = await app.send_document(
            DATABASE_CHANNEL,
            temp_file,
            file_name=new_name,
            thumb=thumb_path if thumb_path else None,
            progress=progress_callback(status_msg, prefix="📤 Uploading:")
        )

        # Use the new private channel numeric ID for all new uploads
        chat_id_to_save = DATABASE_CHANNEL  # DATABASE_CHANNEL must be numeric ID of your private channel

        # ✅ Insert a NEW DB record for the renamed file (clone)
        files_col.insert_one({
            "message_id": sent_msg.id,
            "chat_id": chat_id_to_save,  # store new private channel ID
            "file_unique_id": orig_doc.get("file_unique_id"),
            "user_id": user_id,
            "file_name": new_name,
            "original_file_id": orig_doc.get("message_id"),  # reference to original file
            "timestamp": datetime.datetime.now(datetime.timezone.utc),
            "status": "active"
        })

        # Permanent link for the renamed file (based on new message_id)
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

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")
        return

# ---------------- RENAME COMMAND ----------------
@app.on_message(filters.command("rename"))
async def rename_command(client, message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text("Usage: /rename NewFileName")
        return
    await perform_rename(message.from_user.id, parts[1].strip(), message)

# ---------------- RENAME TEXT REPLY ----------------
@app.on_message(filters.text & ~filters.command(["start", "rename", "set_thumb", "del_thumb", "broadcast"]))
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
