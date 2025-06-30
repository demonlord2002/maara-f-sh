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
DB_CHANNEL_ID = os.getenv("DB_CHANNEL_ID")  # Can be username or ID

DB_FILE = "db.json"
USERS_FILE = "users.json"

for file in [DB_FILE, USERS_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({} if file == USERS_FILE else {}, f)

with open(DB_FILE, "r") as f:
    db = json.load(f)
with open(USERS_FILE, "r") as f:
    allowed_users = json.load(f)

app = Client("madara_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def is_active(user_id):
    if user_id in OWNER_IDS:
        return True
    expiry = allowed_users.get(str(user_id))
    return time.time() < expiry if expiry else False

def _get_duration_seconds(start, end):
    def to_seconds(t):
        h, m, s = map(int, t.split(":"))
        return h * 3600 + m * 60 + s
    return to_seconds(end) - to_seconds(start)

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

@app.on_message(filters.private & filters.command("status"))
async def status_cmd(client, message: Message):
    user_id = message.from_user.id
    expiry = allowed_users.get(str(user_id))
    if not expiry:
        return await message.reply("⛔ You have no active plan. Contact @Madara_Uchiha_lI.")
    remaining = expiry - time.time()
    if remaining <= 0:
        await message.reply("⚠️ Plan expired. Contact @Madara_Uchiha_lI to renew.")
    else:
        d = int(remaining // 86400)
        h = int((remaining % 86400) // 3600)
        m = int((remaining % 3600) // 60)
        await message.reply(f"🔥 Active plan: {d}d {h}h {m}m remaining")

@app.on_message(filters.private & filters.command("sample"))
async def trim_sample(client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        return await message.reply("⚠️ Please reply to a video file with:\n/sample HH:MM:SS to HH:MM:SS")

    user_id = message.from_user.id
    if not is_active(user_id):
        return await message.reply("🚫 Access denied. Please activate your plan.")

    match = re.match(r"/sample (\d{2}:\d{2}:\d{2}) to (\d{2}:\d{2}:\d{2})", message.text)
    if not match:
        return await message.reply("⚠️ Invalid format. Use:\n/sample HH:MM:SS to HH:MM:SS")

    start, end = match.groups()
    duration = _get_duration_seconds(start, end)
    if duration > 120:
        return await message.reply("⚠️ Max sample duration is 2 minutes.")

    temp_filename = f"video_{message.reply_to_message.id}"
    try:
        status = await message.reply("📥 Downloading video...")
        downloaded = await message.reply_to_message.download(file_name=temp_filename)

        if not downloaded:
            return await status.edit("❌ Download failed. File not saved properly.")

        trimmed_name = f"sample_{message.reply_to_message.id}.mp4"
        await status.edit("✂️ Trimming sample video...")

        cmd = ["ffmpeg", "-ss", start, "-i", downloaded, "-t", str(duration), "-c", "copy", "-y", trimmed_name]
        process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await process.communicate()

        if not os.path.exists(trimmed_name):
            await status.edit("⚠️ Fast trim failed, retrying with safe mode...")
            cmd = ["ffmpeg", "-ss", start, "-i", downloaded, "-t", str(duration), "-c:v", "libx264", "-c:a", "aac", "-preset", "fast", "-y", trimmed_name]
            process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            await process.communicate()

        if os.path.exists(trimmed_name):
            await client.send_video(chat_id=message.chat.id, video=trimmed_name, caption="🎬 Sample trimmed successfully!")
            await status.delete()
        else:
            await status.edit("❌ Failed to generate sample. Please check timestamps.")

    except Exception as e:
        await message.reply(f"❌ Error: {e}")
    finally:
        for f in [temp_filename, trimmed_name]:
            if os.path.exists(f):
                os.remove(f)

@app.on_message(filters.command("addusers") & filters.private)
async def add_user(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only Madara can add users.")
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("⚠️ Usage: /addusers <telegram_user_id>")
    user = parts[1]
    allowed_users[user] = time.time() + 28 * 86400
    with open(USERS_FILE, "w") as f:
        json.dump(allowed_users, f)
    await message.reply(f"✅ User `{user}` added for 28 days.")

@app.on_message(filters.command("delusers") & filters.private)
async def del_user(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only Madara can remove users.")
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("⚠️ Usage: /delusers <telegram_user_id>")
    user = parts[1]
    if user in allowed_users:
        del allowed_users[user]
        with open(USERS_FILE, "w") as f:
            json.dump(allowed_users, f)
        await message.reply(f"✅ User `{user}` removed.")
    else:
        await message.reply("ℹ️ User not found.")

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

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_handler(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Not authorized.")
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

@app.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def save_file(client, message: Message):
    user_id = message.from_user.id
    if not is_active(user_id):
        return await message.reply("🚫 You don’t have access. Activate your plan.")
    file_id = str(message.id)
    try:
        saved = await message.copy(chat_id=DB_CHANNEL_ID)
        db[file_id] = {"chat_id": DB_CHANNEL_ID, "msg_id": saved.id}
        with open(DB_FILE, "w") as f:
            json.dump(db, f)
        bot_username = (await app.get_me()).username
        link = f"https://t.me/{bot_username}?start={file_id}"
        await message.reply(f"✅ File sealed successfully!\n📎 Link: {link}")
    except Exception as e:
        await message.reply(f"❌ Failed to save file: {e}")

print("🩸 MADARA FILE SHARE BOT is summoning forbidden chakra...")
app.run()
