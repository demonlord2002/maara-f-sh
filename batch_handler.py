# batch_handler.py

import asyncio
from uuid import uuid4
from datetime import datetime

from pyrogram import filters
from pyrogram.types import Message

from database import save_batch, get_batch
from config import Config  
from bot import bot  # or from your main bot instance

# Temporary file cache per uploader
temp_batches = {}

# Save batch and generate shareable link
@bot.on_message(filters.private & filters.command("save"))
async def save_batch_cmd(client, message: Message):
    user_id = message.from_user.id
     if user_id != Config.OWNER_ID:
        return await message.reply("❌ Only the owner can save batches.")
    if user_id not in temp_batches or not temp_batches[user_id]:
        return await message.reply("⚠️ No files to save. Send files first.")
    
    batch_id = f"batch_{uuid4().hex[:6]}"
    await save_batch(batch_id, temp_batches[user_id], user_id)
    temp_batches.pop(user_id)

    bot_username = (await bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={batch_id}"
    await message.reply(f"✅ Batch saved!\n📎 Link: `{link}`")

# Handle file uploads to batch
@bot.on_message(filters.private & filters.document)
async def handle_batch_files(client, message: Message):
    user_id = message.from_user.id
    if user_id != Config.OWNER_ID:
        return
    if user_id not in temp_batches:
        temp_batches[user_id] = []
    temp_batches[user_id].append({
        "file_id": message.document.file_id,
        "file_name": message.document.file_name
    })
    await message.reply("📎 File added to batch.\nType /save to get the link.")

# Handle /start with batch ID
@bot.on_message(filters.private & filters.command("start"))
async def handle_start(client, message: Message):
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("batch_"):
        batch_id = args[1]
        data = await get_batch(batch_id)
        if not data:
            return await message.reply("❌ Invalid batch ID.")
        files = data["files"]
        await message.reply(f"📦 Batch `{batch_id}` found!\nFiles: {len(files)}")
        for f in files:
            await message.reply_document(f['file_id'], caption=f['file_name'])
