from pyrogram import Client, filters
from pyrogram.types import Message
import os

BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
API_ID = int(os.getenv("APP_ID"))
API_HASH = os.getenv("API_HASH")
OWNER_ID = int(os.getenv("OWNER_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

app = Client("FileShareBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

@app.on_message(filters.private & filters.document)
async def save_file(client, message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ You are not authorized to use this bot.")

    file = message.document
    sent_msg = await client.send_document(
        chat_id=CHANNEL_ID,
        document=file.file_id,
        caption=f"📁 {file.file_name}"
    )
    share_link = f"https://t.me/c/{str(CHANNEL_ID)[4:]}/{sent_msg.message_id}"
    await message.reply(f"✅ File stored!
🔗 Shareable Link:
{share_link}")

@app.on_message(filters.command("start") & filters.private)
async def start_msg(client, message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ You are not authorized to use this bot.")
    await message.reply("👋 Welcome! Send me a file and I'll give you a shareable link.")

app.run()
