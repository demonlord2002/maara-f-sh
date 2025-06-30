# Madara Uchiha File Share Bot (Ubuntu VPS version)

from pyrogram import Client, filters
from pyrogram.types import Message
import os, json, time, re, subprocess, asyncio
from dotenv import load_dotenv

load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_IDS = list(map(int, os.getenv("OWNER_IDS").split(",")))

DB_FILE = "db.json"
USERS_FILE = "users.json"

# Create files if not exist
for file in [DB_FILE, USERS_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({} if file == USERS_FILE else {}, f)

# Load data
with open(DB_FILE, "r") as f:
    db = json.load(f)
with open(USERS_FILE, "r") as f:
    allowed_users = json.load(f)

app = Client("madara_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Function to check if user is active
def is_active(user_id):
    if user_id in OWNER_IDS:
        return True
    expiry = allowed_users.get(str(user_id))
    if not expiry:
        return False
    return time.time() < expiry

# Helper to calculate duration in seconds
def _get_duration_seconds(start, end):
    def to_seconds(t):
        h, m, s = map(int, t.split(":"))
        return h * 3600 + m * 60 + s
    return to_seconds(end) - to_seconds(start)

# /start command
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
            "**🩸 Madara Uchiha File Share Bot**\n\n"
            "Drop your files like a shinobi, share like a legend 💀\n"
            "Only Uchiha-blessed users can create secret links.\n\n"
            "📌 Send any file to receive a private sharing link.\n"
            "⏳ Use /status to check your plan time."
        )

# /status command
@app.on_message(filters.private & filters.command("status"))
async def status_cmd(client, message: Message):
    user_id = message.from_user.id
    expiry = allowed_users.get(str(user_id))
    if not expiry:
        await message.reply("⛔ You have no active plan.\nSpeak to @Madara_Uchiha_lI to unlock forbidden power.")
        return
    remaining = expiry - time.time()
    if remaining <= 0:
        await message.reply("🩸 Your power has faded.\n⚠️ Plan expired. Contact @Madara_Uchiha_lI to reactivate.")
    else:
        days = int(remaining // 86400)
        hours = int((remaining % 86400) // 3600)
        minutes = int((remaining % 3600) // 60)
        await message.reply(f"🔥 Your Sharing Jutsu is active!\n⏱ Time left: {days}d {hours}h {minutes}m")

# /addusers command
@app.on_message(filters.private & filters.command("addusers"))
async def add_user(client, message: Message):
    user_id = message.from_user.id
    if user_id not in OWNER_IDS:
        return await message.reply("❌ Only Madara can add warriors.")
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("⚠️ Usage: /addusers <telegram_user_id>")
    new_user = parts[1]
    expiry_time = time.time() + 28 * 86400
    allowed_users[new_user] = expiry_time
    with open(USERS_FILE, "w") as f:
        json.dump(allowed_users, f)
    await message.reply(f"✅ Shinobi `{new_user}` granted 28 days of power.")

# /delusers command
@app.on_message(filters.private & filters.command("delusers"))
async def del_user(client, message: Message):
    user_id = message.from_user.id
    if user_id not in OWNER_IDS:
        return await message.reply("❌ Only Madara can revoke access.")
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("⚠️ Usage: /delusers <telegram_user_id>")
    del_user = parts[1]
    if del_user not in allowed_users:
        return await message.reply("ℹ️ User not found in the sharing realm.")
    del allowed_users[del_user]
    with open(USERS_FILE, "w") as f:
        json.dump(allowed_users, f)
    await message.reply(f"✅ User `{del_user}` erased from access.")

# /getusers command
@app.on_message(filters.command("getusers") & filters.private)
async def get_users(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Forbidden scroll. Only Madara may open.")
    if not allowed_users:
        return await message.reply("⚠️ No shinobi recruited yet.")
    user_list = "**👤 Uchiha Sharing Squad:**\n\n"
    for uid in allowed_users:
        user_list += f"- `{uid}` — [Click Here](tg://user?id={uid})\n"
    await message.reply(user_list, disable_web_page_preview=True)

# /help command
@app.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message: Message):
    await message.reply(
        "**⚙️ Uchiha Bot Commands:**\n\n"
        "🔹 /start — Begin your session or get shared file\n"
        "🔹 /status — View remaining plan time\n"
        "🔹 /addusers <id> — (Owner) Give 28-day access\n"
        "🔹 /delusers <id> — (Owner) Remove access\n"
        "🔹 /getusers — (Owner) List allowed users\n"
        "🔹 /broadcast <msg> — (Owner) DM all users\n"
        "🔹 /sample HH:MM:SS to HH:MM:SS — Trim sample from replied video"
    )

# /broadcast command
@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_handler(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Forbidden. You're not the ghost of Uchiha.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply("❗ Usage:\n/broadcast Your message here")
    sent, failed = 0, 0
    for user_id in allowed_users:
        try:
            await client.send_message(int(user_id), parts[1])
            sent += 1
        except:
            failed += 1
    await message.reply(f"📢 Message sent.\n✅ Success: {sent}\n❌ Failed: {failed}")

# File upload handler
@app.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def save_file(client, message: Message):
    user_id = message.from_user.id
    if not is_active(user_id):
        return await message.reply("🚫 Forbidden scroll upload attempt blocked.\nActivate your plan to use Sharingan Files.")
    file_id = str(message.id)
    db[file_id] = {"chat_id": message.chat.id, "msg_id": message.id}
    with open(DB_FILE, "w") as f:
        json.dump(db, f)
    bot_username = (await app.get_me()).username
    link = f"https://t.me/{bot_username}?start={file_id}"
    await message.reply(f"✅ File sealed successfully!\n📎 Link: {link}")

# /sample command with subprocess error handling
@app.on_message(filters.private & filters.command("sample") & filters.reply)
async def sample_video(client, message: Message):
    if not is_active(message.from_user.id):
        return await message.reply("🚫 You are not authorized to use this feature.")

    replied = message.reply_to_message
    if not (replied.video or (replied.document and replied.document.mime_type.startswith("video"))):
        return await message.reply("⚠️ Please reply to a video or video file with `/sample HH:MM:SS to HH:MM:SS`")

    match = re.search(r"/sample (\d{1,2}:\d{2}:\d{2}) to (\d{1,2}:\d{2}:\d{2})", message.text)
    if not match:
        return await message.reply("⚠️ Incorrect format.\nUse: `/sample HH:MM:SS to HH:MM:SS`")

    start_time = match.group(1)
    end_time = match.group(2)

    input_path = f"{replied.video.file_unique_id if replied.video else replied.document.file_unique_id}.mp4"
    output_path = f"sample_{input_path}"

    await message.reply("📥 Downloading video...")

    try:
        await replied.download(file_name=input_path)
    except Exception as e:
        return await message.reply(f"❌ Failed to download: `{str(e)}`")

    for _ in range(10):
        if os.path.exists(input_path):
            break
        await asyncio.sleep(0.5)

    if not os.path.exists(input_path):
        return await message.reply("❌ Download failed. File not saved properly.")

    await message.reply("✂️ Trimming sample video...")
    duration = _get_duration_seconds(start_time, end_time)

    try:
        subprocess.run(
            f"ffmpeg -y -ss {start_time} -i {input_path} -t {duration} -c copy -avoid_negative_ts make_zero -preset ultrafast {output_path}",
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as e:
        await message.reply("⚠️ Fast trim failed, retrying with safe mode...")
        try:
            subprocess.run(
                f"ffmpeg -y -ss {start_time} -i {input_path} -t {duration} -c:v libx264 -c:a aac -preset fast {output_path}",
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as e:
            return await message.reply(f"❌ Failed to generate sample.\nError: `{e.stderr.decode().strip()}`")

    if not os.path.exists(output_path):
        return await message.reply("❌ Sample file missing after processing.")

    await message.reply("📤 Uploading sample...")
    await client.send_video(
        chat_id=message.chat.id,
        video=output_path,
        caption=f"🎞️ Sample from {start_time} to {end_time}",
        supports_streaming=True
    )

    os.remove(input_path)
    os.remove(output_path)

print("🩸 MADARA FILE SHARE BOT is summoning forbidden chakra...")
app.run()
