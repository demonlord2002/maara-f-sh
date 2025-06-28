from pyrogram import Client, filters
from pyrogram.types import Message
import os, json
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_IDS = list(map(int, os.getenv("OWNER_IDS").split(",")))

DB_FILE = "db.json"

if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({}, f)

with open(DB_FILE, "r") as f:
    db = json.load(f)

app = Client("madara_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

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
        await message.reply(
            """**🔥 𝙈𝘼𝘿𝘼𝙍𝘼 𝙐𝘾𝙃𝙄𝙃𝘼 𝘼𝙏𝙏𝙄𝙏𝙐𝘿𝙀 𝘽𝙊𝙏**

👋 Send any file to get a **private share link**.
🔐 Only selected users can upload files.
📎 Shareable files never expire unless deleted.

— 💀 Powered by Madara"""
        )

@app.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def save_file(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        await message.reply("🚫 You're not allowed to upload files.")
        return

    file_id = str(message.id)
    db[file_id] = {
        "chat_id": message.chat.id,
        "msg_id": message.id
    }

    with open(DB_FILE, "w") as f:
        json.dump(db, f)

    bot_username = (await app.get_me()).username
    link = f"https://t.me/{bot_username}?start={file_id}"
    await message.reply(f"✅ File saved! 📁 {file_name}")

📎 Link:
{link}")

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_handler(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ You are not allowed to use this command.")

    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        return await message.reply("❗ Send like this:
`/broadcast Your message here`")

    sent = 0
    failed = 0
    for file_info in db.values():
        try:
            await client.send_message(file_info["chat_id"], text[1])
            sent += 1
        except:
            failed += 1
    await message.reply(f"📢 Broadcast finished.
✅ Sent: {sent}
❌ Failed: {failed}")

print("✅ MADARA FILE SHARE BOT is running...")
app.run()
