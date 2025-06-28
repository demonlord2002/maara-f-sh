# 📁 File: bot.py
from pyrogram import Client, filters
from pyrogram.types import Message
import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

bot = Client("MadaraFileBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

files = {}

@bot.on_message(filters.private & filters.document)
async def save_file(_, msg: Message):
    if msg.from_user.id != OWNER_ID:
        return await msg.reply("❌ Only the owner can store files.")
    file_id = msg.document.file_id
    message = await msg.forward(OWNER_ID)
    files[file_id] = message.id
    await msg.reply(f"✅ File saved! Share this link: https://t.me/{bot.me.username}?start={file_id}")

@bot.on_message(filters.command("start") & filters.private)
async def send_file(_, msg: Message):
    if len(msg.command) == 2:
        file_id = msg.command[1]
        try:
            await bot.send_cached_media(msg.chat.id, file_id)
        except Exception:
            await msg.reply("⚠️ File not found or has been deleted.")
    else:
        await msg.reply("👋 Welcome! Send a file to get a shareable link.")

bot.run()
