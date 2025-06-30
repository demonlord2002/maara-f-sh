import os
import json
import time
import re
import asyncio
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_IDS = list(map(int, os.getenv("OWNER_IDS").split(",")))
DB_CHANNEL_ID = os.getenv("DB_CHANNEL_ID")  # Use @channelusername or -100...

DB_FILE = "db.json"
USERS_FILE = "users.json"

for file in [DB_FILE, USERS_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

with open(DB_FILE, "r") as f:
    db = json.load(f)
with open(USERS_FILE, "r") as f:
    allowed_users = json.load(f)

app = Client("madara_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def is_active(user_id):
    if user_id in OWNER_IDS:
        return True
    expiry = allowed_users.get(str(user_id))
    return expiry and time.time() < expiry

@app.on_message(filters.command("sample") & filters.private)
async def sample_video(client, message: Message):
    if not message.reply_to_message or not (message.reply_to_message.video or message.reply_to_message.document):
        return await message.reply("⚠️ Please reply to a video file with:\n/sample HH:MM:SS to HH:MM:SS")

    match = re.match(r"/sample\s+(\d{2}:\d{2}:\d{2})\s+to\s+(\d{2}:\d{2}:\d{2})", message.text)
    if not match:
        return await message.reply("⚠️ Invalid format. Use:\n/sample HH:MM:SS to HH:MM:SS")

    start, end = match.groups()
    start_sec = sum(x * int(t) for x, t in zip([3600, 60, 1], start.split(":")))
    end_sec = sum(x * int(t) for x, t in zip([3600, 60, 1], end.split(":")))
    duration = end_sec - start_sec

    if duration <= 0 or duration > 60:
        return await message.reply("⚠️ Invalid duration. Max 60 seconds allowed.")

    msg = await message.reply("📥 Downloading video...")
    try:
        input_file = await message.reply_to_message.download()
    except:
        return await msg.edit("❌ Failed to download video file.")

    output = "sample.mp4"
    cmd = [
        "ffmpeg", "-y", "-ss", start, "-i", input_file, "-t", str(duration),
        "-c:v", "libx264", "-c:a", "aac", "-preset", "ultrafast", output
    ]

    await msg.edit("✂️ Trimming sample video...")
    try:
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.communicate()
    except:
        return await msg.edit("❌ Failed to trim video. ffmpeg error.")

    if os.path.exists(output):
        await client.send_video(chat_id=message.chat.id, video=output, caption="🎬 Here's your sample.")
        os.remove(output)
        os.remove(input_file)
        await msg.delete()
    else:
        await msg.edit("❌ Failed to generate sample. Try again.")

@app.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def save_file(client, message: Message):
    user_id = message.from_user.id
    if not is_active(user_id):
        return await message.reply("🚫 Forbidden. Contact @Madara_Uchiha_lI to activate access.")

    file_id = str(message.id)
    try:
        saved = await message.copy(chat_id=DB_CHANNEL_ID)
        db[file_id] = {"chat_id": DB_CHANNEL_ID, "msg_id": saved.id}
        with open(DB_FILE, "w") as f:
            json.dump(db, f)
        bot_username = (await app.get_me()).username
        link = f"https://t.me/{bot_username}?start={file_id}"
        await message.reply(f"✅ File sealed!\n📎 Link: {link}")
    except Exception as e:
        await message.reply(f"❌ Failed to save file: {e}")

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    args = message.text.split()
    if len(args) == 2:
        file_id = args[1]
        if file_id in db:
            file_info = db[file_id]
            await client.copy_message(chat_id=message.chat.id, from_chat_id=file_info["chat_id"], message_id=file_info["msg_id"])
        else:
            await message.reply("❌ File not found or expired.")
    else:
        await message.reply("**🩸 Madara Uchiha File Share Bot**\n\nSend a file to get a shareable link.\nUse /sample HH:MM:SS to HH:MM:SS on a replied video to trim a sample.")

print("🩸 MADARA FILE SHARE BOT READY")
app.run()
