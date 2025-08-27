from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.enums import ParseMode
from pymongo import MongoClient
from config import *
import datetime
import asyncio
import re
import os
import time
import traceback
import subprocess

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

        async def edit():
            async with lock:
                try:
                    await status_message.edit_text(text)
                except:
                    pass

        asyncio.run_coroutine_threadsafe(edit(), app.loop)

    return callback

# ---------------- GET DURATION IN SECONDS ----------------
def get_duration_seconds(start_str, end_str):
    h1, m1, s1 = map(int, start_str.split(":"))
    h2, m2, s2 = map(int, end_str.split(":"))
    start_sec = h1 * 3600 + m1 * 60 + s1
    end_sec = h2 * 3600 + m2 * 60 + s2
    return end_sec - start_sec

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
        f"📂 𝗦𝗲𝗻𝗱 𝗺𝗲 𝗮𝗻𝘆 𝗳𝗶𝗹𝗲 & 𝗜’𝗹𝗹 𝗰𝗿𝗲𝗮𝘁𝗲 𝗮 𝘀𝗵𝗮𝗿𝗲𝗮𝗯𝗹𝗲 𝗹𝗶𝗻𝗸 ⚡",
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
        f"💡 **Do you want to rename, get link or create a sample video?**\n\n"
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
    file_doc = files_col.find_one({"file_id": file_id})
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
@app.on_message(filters.command("sample"))
async def sample_trim(client, message: Message):
    if not message.reply_to_message or not (
        message.reply_to_message.video or message.reply_to_message.document
    ):
        return await message.reply("⚠️ Please reply to a video file with:\n/sample HH:MM:SS to HH:MM:SS")

    match = re.search(r"(\d{2}:\d{2}:\d{2})\s+to\s+(\d{2}:\d{2}:\d{2})", message.text)
    if not match:
        return await message.reply("❌ Invalid format. Use:\n/sample 00:10:00 to 00:10:30")

    start, end = match.group(1), match.group(2)
    duration = get_duration_seconds(start, end)
    if duration <= 0 or duration > 60:
        return await message.reply("⚠️ Duration must be between 1–60 seconds.")

    msg = await message.reply("📥 Downloading video...")

    try:
        input_path = await message.reply_to_message.download()
    except Exception:
        return await msg.edit("❌ Download failed. File not saved properly.")

    output_path = f"/tmp/sample_clip_{message.from_user.id}.mp4"

    # Fast trim
    await msg.edit("✂️ Trimming sample video (fast mode)...")
    fast_cmd = [
        "ffmpeg", "-ss", start, "-i", input_path, "-t", str(duration),
        "-c", "copy", output_path, "-y"
    ]
    process = await asyncio.create_subprocess_exec(*fast_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    await process.communicate()

    # Fallback if needed
    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        await msg.edit("⚠️ Fast trim failed, retrying with safe mode...")
        slow_cmd = [
            "ffmpeg", "-i", input_path, "-ss", start, "-t", str(duration),
            "-c:v", "libx264", "-c:a", "aac", output_path, "-y"
        ]
        process = await asyncio.create_subprocess_exec(*slow_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        await process.communicate()

    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        os.remove(input_path)
        return await msg.edit("❌ Failed to generate sample. Please check the video format.")

    await msg.edit("📤 Uploading sample...")
    await client.send_video(
        chat_id=message.chat.id,
        video=output_path,
        caption=f"✂️ Sample clip from {start} to {end}"
    )

    os.remove(input_path)
    os.remove(output_path)

# ---------------- (REMAINING ORIGINAL BOT LOGIC BELOW) ----------------
# Include all your rename, link, set_thumb, del_thumb, broadcast logic here as is.
# For brevity, I’m not repeating the full original code, but nothing else changes.

print("🔥 Madara File Sharing Bot running safely on Heroku...")
app.run()
