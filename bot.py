# Madara Uchiha File Share Bot (Ubuntu VPS version)

from pyrogram import Client, filters
from pyrogram.types import Message
import os, json, time, re
from dotenv import load_dotenv

load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_IDS = list(map(int, os.getenv("OWNER_IDS").split(",")))
DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID"))  # Private channel ID

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

# Check access
def is_active(user_id):
    if user_id in OWNER_IDS:
        return True
    expiry = allowed_users.get(str(user_id))
    return expiry and time.time() < expiry

# Helper for duration

def _get_duration_seconds(start, end):
    def to_seconds(t):
        h, m, s = map(int, t.split(":"))
        return h * 3600 + m * 60 + s
    return to_seconds(end) - to_seconds(start)

# /start
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
            "**🌸 Madara Uchiha File Share Bot**\n\n"
            "Drop your files like a shinobi, share like a legend 💀\n"
            "Only Uchiha-blessed users can create secret links.\n\n"
            "📌 Send any file to receive a private sharing link.\n"
            "⏳ Use /status to check your plan time."
        )

# /status
@app.on_message(filters.private & filters.command("status"))
async def status_cmd(client, message: Message):
    user_id = message.from_user.id
    expiry = allowed_users.get(str(user_id))
    if not expiry:
        return await message.reply("⛔️ You have no active plan.\nSpeak to @Madara_Uchiha_lI to unlock forbidden power.")
    remaining = expiry - time.time()
    if remaining <= 0:
        await message.reply("🌸 Your power has faded.\n⚠️ Plan expired. Contact @Madara_Uchiha_lI to reactivate.")
    else:
        d = int(remaining // 86400)
        h = int((remaining % 86400) // 3600)
        m = int((remaining % 3600) // 60)
        await message.reply(f"🔥 Your Sharing Jutsu is active!\n🕱 Time left: {d}d {h}h {m}m")

# /addusers
@app.on_message(filters.private & filters.command("addusers"))
async def add_user(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only Madara can add warriors.")
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("⚠️ Usage: /addusers <telegram_user_id>")
    new_user = parts[1]
    allowed_users[new_user] = time.time() + 28 * 86400
    with open(USERS_FILE, "w") as f:
        json.dump(allowed_users, f)
    await message.reply(f"✅ Shinobi `{new_user}` granted 28 days of power.")

# /delusers
@app.on_message(filters.private & filters.command("delusers"))
async def del_user(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
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

# /getusers
@app.on_message(filters.command("getusers") & filters.private)
async def get_users(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Forbidden scroll. Only Madara may open.")
    if not allowed_users:
        return await message.reply("⚠️ No shinobi recruited yet.")
    msg = "**👤 Uchiha Sharing Squad:**\n\n"
    for uid in allowed_users:
        msg += f"- `{uid}` — [Click](tg://user?id={uid})\n"
    await message.reply(msg, disable_web_page_preview=True)

# /help
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

# /broadcast
@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_handler(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Forbidden. You're not the ghost of Uchiha.")
    if len(message.text.split(maxsplit=1)) < 2:
        return await message.reply("❗ Usage:\n/broadcast Your message here")
    sent, failed = 0, 0
    for user_id in allowed_users:
        try:
            await client.send_message(int(user_id), message.text.split(maxsplit=1)[1])
            sent += 1
        except:
            failed += 1
    await message.reply(f"📢 Message sent.\n✅ Success: {sent}\n❌ Failed: {failed}")

# File upload with DB channel
@app.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def save_file(client, message: Message):
    if not is_active(message.from_user.id):
        return await message.reply("🛑 Forbidden scroll upload attempt blocked.\nActivate your plan to use Sharingan Files.")
    file_id = str(message.id)
    saved = await message.copy(chat_id=DB_CHANNEL_ID)
    db[file_id] = {"chat_id": DB_CHANNEL_ID, "msg_id": saved.id}
    with open(DB_FILE, "w") as f:
        json.dump(db, f)
    bot_username = (await app.get_me()).username
    link = f"https://t.me/{bot_username}?start={file_id}"
    await message.reply(f"✅ File sealed successfully!\n📌 Link: {link}")

# /sample command
@app.on_message(filters.private & filters.command("sample"))
async def sample_cmd(client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        return await message.reply(
            "⚠️ Please reply to a **video file** with:\n`/sample HH:MM:SS to HH:MM:SS`",
            quote=True
        )

    match = re.match(r"/sample (\d{2}:\d{2}:\d{2}) to (\d{2}:\d{2}:\d{2})", message.text)
    if not match:
        return await message.reply("❌ Invalid format.\nUse: `/sample 00:01:00 to 00:01:30`", quote=True)

    start_time, end_time = match.groups()
    duration = _get_duration_seconds(start_time, end_time)

    if duration <= 0 or duration > 300:
        return await message.reply("⚠️ Duration must be between 1 and 300 seconds (5 mins max)")

    user_id = message.from_user.id
    if not is_active(user_id):
        return await message.reply("🚫 Forbidden. Activate your Sharingan plan.")

    status = await message.reply("📥 Downloading video...")

    folder = f"downloads/sample_{user_id}"
    os.makedirs(folder, exist_ok=True)

    input_path = os.path.join(folder, "input.mp4")
    output_path = os.path.join(folder, "output.mp4")

    try:
        await message.reply_to_message.download(file_name=input_path)
    except Exception as e:
        return await status.edit("❌ Download failed. File not saved properly.")

    await status.edit("✂️ Trimming sample video...")

    fast_cmd = f"ffmpeg -ss {start_time} -i '{input_path}' -t {duration} -c copy -avoid_negative_ts 1 '{output_path}' -y"
    result = os.system(fast_cmd)

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        await status.edit("⚠️ Fast trim failed, retrying with safe mode...")
        safe_cmd = f"ffmpeg -ss {start_time} -i '{input_path}' -t {duration} -c:v libx264 -c:a aac '{output_path}' -y"
        os.system(safe_cmd)

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        return await status.edit("❌ Failed to generate sample. Please check timestamps or input file.")

    await status.edit("📤 Uploading trimmed sample...")
    await message.reply_video(output_path, caption="🎬 Sample trimmed by Madara Uchiha Bot 🩸")

    try:
        os.remove(input_path)
        os.remove(output_path)
        os.rmdir(folder)
    except:
        pass

print("🩸 MADARA FILE SHARE BOT is summoning forbidden chakra...")
app.run()
