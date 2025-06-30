import os
import json
import time
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_IDS = list(map(int, os.getenv("OWNER_IDS").split(",")))
DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID"))

DB_FILE = "db.json"
USERS_FILE = "users.json"

# Create files if not exist
for file in [DB_FILE, USERS_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

# Load data
with open(DB_FILE, "r") as f:
    db = json.load(f)
with open(USERS_FILE, "r") as f:
    allowed_users = json.load(f)

app = Client("madara_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def is_active(user_id):
    if user_id in OWNER_IDS:
        return True
    expiry = allowed_users.get(str(user_id))
    if not expiry:
        return False
    return time.time() < expiry

@app.on_message(filters.private & filters.command("start"))
async def start_cmd(client, message: Message):
    args = message.text.split()
    if len(args) == 2:
        file_id = args[1]
        if file_id in db:
            file_info = db[file_id]
            await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=file_info["chat_id"],
                message_id=file_info["msg_id"]
            )
        else:
            await message.reply("❌ File not found or expired.")
    else:
        await message.reply(
            "**🎥 Madara Uchiha File Share Bot**\n\n"
            "Drop your files like a shinobi, share like a legend 💀\n"
            "Only Uchiha-blessed users can create secret links.\n\n"
            "📌 Send any file to receive a private sharing link.\n"
            "⏳ Use /status to check your plan time."
        )

@app.on_message(filters.private & filters.command("status"))
async def status_cmd(client, message: Message):
    user_id = message.from_user.id
    expiry = allowed_users.get(str(user_id))
    if not expiry:
        return await message.reply("⛔️ No active plan. DM @Madara_Uchiha_lI to activate.")
    remaining = expiry - time.time()
    if remaining <= 0:
        return await message.reply("🧨 Plan expired. Contact @Madara_Uchiha_lI to renew.")
    days = int(remaining // 86400)
    hours = int((remaining % 86400) // 3600)
    minutes = int((remaining % 3600) // 60)
    await message.reply(f"🔥 Active Plan!\n⏱️ Time left: {days}d {hours}h {minutes}m")

@app.on_message(filters.private & filters.command("addusers"))
async def add_user(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only owner can add users.")
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("⚠️ Usage: /addusers <telegram_user_id>")
    uid = parts[1]
    allowed_users[uid] = time.time() + 28 * 86400
    with open(USERS_FILE, "w") as f:
        json.dump(allowed_users, f)
    await message.reply(f"✅ User {uid} added for 28 days.")

@app.on_message(filters.private & filters.command("delusers"))
async def del_user(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only owner can remove users.")
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("⚠️ Usage: /delusers <telegram_user_id>")
    uid = parts[1]
    allowed_users.pop(uid, None)
    with open(USERS_FILE, "w") as f:
        json.dump(allowed_users, f)
    await message.reply(f"✅ User {uid} removed.")

@app.on_message(filters.private & filters.command("getusers"))
async def get_users(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Forbidden.")
    users = "\n".join([f"`{uid}`" for uid in allowed_users])
    await message.reply(f"**👥 Allowed Users:**\n{users}")

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message: Message):
    await message.reply(
        "**🛠️ Bot Commands:**\n"
        "- /start\n"
        "- /status\n"
        "- /addusers <id>\n"
        "- /delusers <id>\n"
        "- /getusers\n"
        "- /sample HH:MM:SS to HH:MM:SS (reply to video)"
    )

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_handler(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Forbidden.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply("Usage: /broadcast <message>")
    sent, failed = 0, 0
    for uid in allowed_users:
        try:
            await client.send_message(int(uid), parts[1])
            sent += 1
        except:
            failed += 1
    await message.reply(f"Broadcast complete. ✅ {sent}, ❌ {failed}")

@app.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def save_file(client, message: Message):
    user_id = message.from_user.id
    if not is_active(user_id):
        return await message.reply("❌ Access denied. Contact admin.")
    try:
        sent = await message.copy(chat_id=DB_CHANNEL_ID)
        file_id = str(message.id)
        db[file_id] = {"chat_id": DB_CHANNEL_ID, "msg_id": sent.id}
        with open(DB_FILE, "w") as f:
            json.dump(db, f)
        link = f"https://t.me/{(await app.get_me()).username}?start={file_id}"
        await message.reply(f"✅ File saved!\n📎 Link: {link}")
    except Exception as e:
        await message.reply(f"❌ Failed to save file: {e}")

@app.on_message(filters.private & filters.command("sample"))
async def sample_cmd(client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        return await message.reply("⚠️ Please reply to a video with:\n/sample HH:MM:SS to HH:MM:SS")

    match = re.match(r"/sample (\d{2}:\d{2}:\d{2}) to (\d{2}:\d{2}:\d{2})", message.text)
    if not match:
        return await message.reply("⚠️ Invalid format. Use:\n/sample HH:MM:SS to HH:MM:SS")

    start, end = match.groups()
    input_file = f"sample_{message.message_id}.mp4"
    output_file = f"trimmed_{message.message_id}.mp4"

    await message.reply("📥 Downloading video...")
    try:
        await message.reply_to_message.download(file_name=input_file)
    except Exception as e:
        return await message.reply("❌ Download failed.")

    await message.reply("✂️ Trimming sample video...")
    duration = int(sum(x * int(t) for x, t in zip([3600, 60, 1], end.split(":"))) - sum(x * int(t) for x, t in zip([3600, 60, 1], start.split(":"))))
    ffmpeg_cmd = f"ffmpeg -ss {start} -i '{input_file}' -t {duration} -c copy '{output_file}' -y"

    try:
        process = await asyncio.create_subprocess_shell(ffmpeg_cmd)
        await process.communicate()
        await message.reply_video(output_file, caption=f"🎬 Sample from {start} to {end}")
        os.remove(input_file)
        os.remove(output_file)
    except Exception as e:
        await message.reply(f"❌ Failed to generate sample: {e}")

print("🩸 MADARA FILE SHARE BOT ready.")
app.run()
