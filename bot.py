import os
import json
from pyrogram import Client, filters
from pyrogram.types import Message
from config import TG_BOT_TOKEN, APP_ID, API_HASH, OWNER_ID, CHANNEL_ID
from uuid import uuid4

BOT = Client("FileShareBot", bot_token=TG_BOT_TOKEN, api_id=APP_ID, api_hash=API_HASH)

DB_FILE = "db.json"
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({}, f)

def save_file_mapping(unique_id, file_id):
    with open(DB_FILE, "r") as f:
        data = json.load(f)
    data[unique_id] = file_id
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

def get_file_id(unique_id):
    with open(DB_FILE, "r") as f:
        data = json.load(f)
    return data.get(unique_id)

@BOT.on_message(filters.private & filters.command("start"))
async def start(client, msg: Message):
    args = msg.text.split(" ", 1)
    if len(args) == 2:
        file_id = get_file_id(args[1])
        if file_id:
            await client.copy_message(chat_id=msg.chat.id, from_chat_id=CHANNEL_ID, message_id=int(file_id))
        else:
            await msg.reply("❌ Invalid or expired link.")
    else:
        await msg.reply("📁 Send me a file and I'll generate a shareable link. Only the owner can upload.")

@BOT.on_message(filters.private & filters.media)
async def handle_file(client, msg: Message):
    if msg.from_user.id != OWNER_ID:
        return await msg.reply("❌ Only the owner can upload and share files.")
    forward = await msg.forward(CHANNEL_ID)
    unique_id = str(forward.id)
    save_file_mapping(unique_id, forward.id)
    share_link = f"https://t.me/{client.me.username}?start={unique_id}"
    await msg.reply(f"✅ Share this link: {share_link}")

BOT.run()
