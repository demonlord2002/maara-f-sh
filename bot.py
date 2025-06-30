# ✅ Madara Uchiha File Share Bot (Ubuntu VPS version)

from pyrogram import Client, filters
from pyrogram.types import Message
import os, json, time, re, asyncio, subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_IDS = list(map(int, os.getenv("OWNER_IDS").split(",")))
DB_CHANNEL_ID = os.getenv("DB_CHANNEL_ID")  # username or numeric

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

# Helper functions
def is_active(user_id):
    if user_id in OWNER_IDS:
        return True
    expiry = allowed_users.get(str(user_id))
    return expiry and time.time() < expiry

def get_duration_seconds(start, end):
    def to_sec(t): return sum(x * int(t) for x, t in zip([3600, 60, 1], t.split(":")))
    return to_sec(end) - to_sec(start)

@app.on_message(filters.private & filters.command("start"))
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
        await message.reply(
            "**🩸 Madara Uchiha File Share Bot**\n\n"
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
        return await message.reply("⛔ No active plan. Contact @Madara_Uchiha_lI")
    remaining = expiry - time.time()
    if remaining <= 0:
        return await message.reply("⚠️ Plan expired. Contact @Madara_Uchiha_lI")
    d, h, m = int(remaining // 86400), int((remaining % 86400) // 3600), int((remaining % 3600) // 60)
    await message.reply(f"🔥 Active Plan: {d}d {h}h {m}m")

@app.on_message(filters.private & filters.command("help"))
async def help_cmd(client, message: Message):
    await message.reply(
        "**🩸 Madara Uchiha File Share Bot — Help Menu**\n\n"
        "📌 Send any file to receive a private shareable link.\n"
        "✂️ `/sample HH:MM:SS to HH:MM:SS` — reply to a video to cut a short sample.\n"
        "⏳ `/status` — check your remaining plan time.\n"
        "👤 `/addusers <user_id>` — (owner only) add new user\n"
        "❌ `/delusers <user_id>` — (owner only) remove user\n"
        "📢 `/broadcast <message>` — (owner only) broadcast message to all users\n"
        "📍 `/getusers` — (owner only) list of all users\n"
        "\nOnly Uchiha-blessed users can use secret file share powers 🔥"
    )

@app.on_message(filters.private & filters.command("addusers"))
async def add_user(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only Madara can add warriors.")
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("⚠️ Usage: /addusers <user_id>")
    new_user = parts[1]
    allowed_users[new_user] = time.time() + 28 * 86400
    with open(USERS_FILE, "w") as f:
        json.dump(allowed_users, f)
    await message.reply(f"✅ {new_user} granted 28 days of power.")

@app.on_message(filters.private & filters.command("delusers"))
async def del_user(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only Madara can revoke.")
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("⚠️ Usage: /delusers <user_id>")
    del_user = parts[1]
    if del_user in allowed_users:
        del allowed_users[del_user]
        with open(USERS_FILE, "w") as f:
            json.dump(allowed_users, f)
        await message.reply(f"✅ {del_user} removed.")

@app.on_message(filters.command("getusers") & filters.private)
async def get_users(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Not allowed.")
    if not allowed_users:
        return await message.reply("⚠️ No users.")
    msg = "**👤 Uchiha Sharing Squad:**\n\n"
    msg += "\n".join([f"- `{uid}` [Click](tg://user?id={uid})" for uid in allowed_users])
    await message.reply(msg, disable_web_page_preview=True)

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast(client, message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Forbidden.")
    text = message.text.split(" ", 1)
    if len(text) < 2:
        return await message.reply("❗ Usage: /broadcast Your message")
    sent, failed = 0, 0
    for uid in allowed_users:
        try:
            await client.send_message(int(uid), text[1])
            sent += 1
        except:
            failed += 1
    await message.reply(f"📢 Broadcast Done\n✅ Sent: {sent}\n❌ Failed: {failed}")

@app.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def save_file(client, message: Message):
    if not is_active(message.from_user.id):
        return await message.reply("🚫 You need a plan. Contact @Madara_Uchiha_lI")
    file_id = str(message.id)
    saved = await message.copy(chat_id=DB_CHANNEL_ID)
    db[file_id] = {"chat_id": DB_CHANNEL_ID, "msg_id": saved.id}
    with open(DB_FILE, "w") as f:
        json.dump(db, f)
    link = f"https://t.me/{(await app.get_me()).username}?start={file_id}"
    await message.reply(f"✅ File sealed!\n📎 Link: {link}")

@app.on_message(filters.command("sample") & filters.private)
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
    except Exception as e:
        return await msg.edit("❌ Download failed. File not saved properly.")

    output_path = "sample_clip.mp4"

    # Try fast trim first (copy mode)
    await msg.edit("✂️ Trimming sample video (fast mode)...")
    fast_cmd = [
        "ffmpeg", "-ss", start, "-i", input_path, "-t", str(duration),
        "-c", "copy", output_path, "-y"
    ]
    process = await asyncio.create_subprocess_exec(*fast_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    await process.communicate()

    # If fast mode fails, fallback to re-encode
    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        await msg.edit("⚠️ Fast trim failed, retrying with safe mode...")
        slow_cmd = [
            "ffmpeg", "-i", input_path, "-ss", start, "-t", str(duration),
            "-c:v", "libx264", "-c:a", "aac", output_path, "-y"
        ]
        process = await asyncio.create_subprocess_exec(*slow_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        await process.communicate()

    # Final check and send
    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        os.remove(input_path)
        return await msg.edit("❌ Failed to generate sample. Please check the video format.")

    await msg.edit("📤 Uploading sample...")
    await client.send_video(
        chat_id=message.chat.id,
        video=output_path,
        caption=f"✂️ Sample clip from {start} to {end}"
    )

    # Cleanup
    os.remove(input_path)
    os.remove(output_path)

print("🩸 MADARA FILE SHARE BOT is summoning forbidden chakra...")
app.run()
