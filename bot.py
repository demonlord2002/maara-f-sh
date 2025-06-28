from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID
import json, os

DB_FILE = "db.json"

# Load or create database
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({}, f)

with open(DB_FILE, "r") as f:
    db = json.load(f)

app = Client("file_share_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    args = message.text.split()
    if len(args) == 2:
        file_id = args[1]
        if file_id in db:
            file_info = db[file_id]
            await client.copy_message(message.chat.id, file_info["chat_id"], file_info["msg_id"])
        else:
            await message.reply("❌ File not found or expired.")
    else:
        await message.reply("👋 Hello! Send me any file and I will give you a shareable link.")

@app.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def save_file(client, message: Message):
    file_id = str(message.id)
    db[file_id] = {
        "chat_id": message.chat.id,
        "msg_id": message.message_id
    }
    with open(DB_FILE, "w") as f:
        json.dump(db, f)
    bot_username = (await app.get_me()).username
    link = f"https://t.me/{bot_username}?start={file_id}"
    await message.reply(f"✅ File saved!\n\n📎 Shareable Link:\n{link}")

print("✅ Bot is running. Waiting for Telegram messages...")
app.run()
