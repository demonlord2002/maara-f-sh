# ✅ Madara Uchiha File Share Bot with MongoDB

from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient
import os, time, re, asyncio, subprocess
import string
import random
from dotenv import load_dotenv
from datetime import datetime
from asyncio import TimeoutError
from asyncio import get_event_loop, wait_for
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import MessageNotModified
from config import DB_CHANNEL, MONGO_URL
import uuid



# Store temporary batch sessions in memory
batch_sessions = {}
# Setup MongoDB collection for batch
batch_col = mongo.madara.batch_links

user_steps = {}

# Load .env variables
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_IDS = list(map(int, os.getenv("OWNER_IDS").split(",")))
DB_CHANNEL_ID = os.getenv("DB_CHANNEL_ID")
MONGO_URL = os.getenv("MONGO_URL")

mongo = MongoClient(MONGO_URL)
db = mongo["madara_bot"]
files_col = db["files"]
users_col = db["users"]

app = Client("madara_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Check user access
def is_active(user_id):
    if user_id in OWNER_IDS:
        return True
    u = users_col.find_one({"_id": user_id})
    return u and u.get("expires", 0) > time.time()

def get_duration_seconds(start, end):
    def to_sec(t): return sum(x * int(t) for x, t in zip([3600, 60, 1], t.split(":")))
    return to_sec(end) - to_sec(start)

@app.on_message(filters.private & filters.command("start"))
async def start_cmd(client, message: Message):
    args = message.text.split()

    # If a shared link is used (/start <arg>)
    if len(args) == 2:
        arg_value = args[1]

        # ✅ Batch File Handling
        if arg_value.startswith("batch_"):
            batch_data = batch_col.find_one({"batch_id": arg_value})
            if not batch_data:
                return await message.reply("❌ Invalid or expired batch link.")
            
            start_id = batch_data["start_msg_id"]
            end_id = batch_data["end_msg_id"]
            db_channel = batch_data["db_channel"]

            await message.reply(
                f"📦 Sending your batch files...\nFrom ID `{start_id}` to `{end_id}`"
            )

            for msg_id in range(start_id, end_id + 1):
                try:
                    await client.forward_messages(
                        chat_id=message.chat.id,
                        from_chat_id=db_channel,
                        message_ids=msg_id
                    )
                    await asyncio.sleep(1)
                except Exception as e:
                    await message.reply(f"⚠️ Error sending message ID {msg_id}: {e}")
                    return
            return  # end batch case

        # ✅ Single File Handling
        else:
            file_id = arg_value
            data = files_col.find_one({"_id": file_id})
            if data:
                try:
                    await client.copy_message(
                        chat_id=message.chat.id,
                        from_chat_id=data["chat_id"],
                        message_id=data["msg_id"]
                    )
                except Exception as e:
                    await message.reply(f"⚠️ Failed to send file: {e}")
            else:
                await message.reply("❌ File not found or expired.")
            return

    # ✅ Default Welcome Message
    await message.reply(
        "**🩸 Madara Uchiha File Share Bot**\n\n"
        "Drop your files like a shinobi, share like a legend 💀\n"
        "Only Uchiha-blessed users can create secret links.\n\n"
        "📌 Send any file to receive a private sharing link.\n"
        "🎞 Use `/batch` to create full episode shareable links.\n"
        "⏳ Use `/status` to check your plan time."
    )

        
@app.on_message(filters.private & filters.command("batch"))
async def batch_cmd(client, message: Message):
    user_id = message.from_user.id
    user_steps[user_id] = {"step": 1}
    await message.reply("📌 Please reply with the **first message link** (e.g., https://t.me/channel/123):")

@app.on_message(filters.private & filters.text)
async def handle_batch_steps(client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_steps:
        return

    step_data = user_steps[user_id]

    # Step 1: First message link
    if step_data["step"] == 1:
        link = message.text.strip()
        match = re.search(r"https://t.me/([\w_]+)/(\d+)", link)
        if not match:
            return await message.reply("❌ Invalid first message link. Try again.")

        step_data["channel"] = match.group(1)
        step_data["start_id"] = int(match.group(2))
        step_data["step"] = 2
        await message.reply("✅ First link saved.\n\n📌 Now send the **last message link**:")
    
    # Step 2: Last message link
    elif step_data["step"] == 2:
        link = message.text.strip()
        match = re.search(r"https://t.me/([\w_]+)/(\d+)", link)
        if not match:
            return await message.reply("❌ Invalid last message link. Try again.")

        step_data["end_id"] = int(match.group(2))
        if step_data["end_id"] < step_data["start_id"]:
            return await message.reply("⚠️ Last message ID must be greater than or equal to the first.")

        # Save batch info to DB
        batch_id = f"{user_id}_{step_data['start_id']}_{step_data['end_id']}"
        batch_col.insert_one({
            "batch_id": batch_id,
            "user_id": user_id,
            "db_channel": step_data["channel"],
            "start_msg_id": step_data["start_id"],
            "end_msg_id": step_data["end_id"]
        })

        del user_steps[user_id]  # cleanup
        share_link = f"https://t.me/{client.me.username}?start=batch_{batch_id}"
        await message.reply(f"✅ Batch created successfully!\n\n🔗 Share this link:\n`{share_link}`")





@app.on_message(filters.private & filters.command("status"))
async def status_cmd(client, message: Message):
    user_id = message.from_user.id
    data = users_col.find_one({"_id": user_id})
    if not data:
        return await message.reply("⛔ No active plan. Contact @Madara_Uchiha_lI")
    remaining = data["expires"] - time.time()
    if remaining <= 0:
        return await message.reply("⚠️ Plan expired. Contact @Madara_Uchiha_lI")
    d, h, m = int(remaining // 86400), int((remaining % 86400) // 3600), int((remaining % 3600) // 60)
    await message.reply(f"🔥 Active Plan: {d}d {h}h {m}m")

@app.on_message(filters.private & filters.command("addusers"))
async def add_user(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only Madara can add warriors.")
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("⚠️ Usage:/addusers <user_id>")
    uid = int(parts[1])
    users_col.update_one({"_id": uid}, {"$set": {"expires": time.time() + 28 * 86400}}, upsert=True)
    await message.reply(f"✅ {uid} granted 28 days of power.")

@app.on_message(filters.private & filters.command("delusers"))
async def del_user(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only Madara can revoke.")
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("⚠️ Usage: /delusers <user_id>")
    users_col.delete_one({"_id": int(parts[1])})
    await message.reply(f"✅ {parts[1]} removed.")

@app.on_message(filters.command("getusers") & filters.private)
async def get_users(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Forbidden.")
    users = users_col.find()
    text = "**👤 Uchiha Sharing Squad:**\n\n"
    for u in users:
        text += f"- {u['_id']} — [Click](tg://user?id={u['_id']})\n"
    await message.reply(text, disable_web_page_preview=True)

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_handler(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only Madara can shout to the Shinobi world.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply("⚠️ Usage: /broadcast your message here")
    sent, failed = 0, 0
    for user in users_col.find():
        try:
            await client.send_message(int(user['_id']), parts[1])
            sent += 1
        except:
            failed += 1
    await message.reply(f"📢 Broadcast Completed!\n✅ Sent: {sent}\n❌ Failed: {failed}")

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message: Message):
    if not is_active(message.from_user.id):
        return await message.reply("🚫 You are not a recognized Uchiha warrior.\n💬 Contact @Madara_Uchiha_lI to unlock your power.")
    await message.reply(
        "**🩸 MADARA UCHIHA - COMMAND SCROLL ⚔️**\n\n"
        "**👤 USER COMMANDS:**\n"
        "🧿 /start – Access shared files using links\n"
        "⏳ /status – Check your remaining plan time\n"
        "📎 *Send a file* – Get a secret sharing link\n"
        "✂️ /sample HH:MM:SS to HH:MM:SS – Trim sample from replied video\n\n"
        "**👑 OWNER COMMANDS:**\n"
        "👥 /addusers <id> – Grant 28 days access\n"
        "🚫 /delusers <id> – Revoke a user\n"
        "📜 /getusers – Show all allowed users\n"
        "📢 /broadcast <msg> – DM all active users\n\n"
        "🔐 *Only true Uchihas can rule the darkness.*"
    )
    
@app.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def save_file(client, message: Message):
    if not is_active(message.from_user.id):
        return await message.reply("🚫 Plan expired. Contact @Madara_Uchiha_lI")
    file_id = str(message.id)
    saved = await message.copy(chat_id=DB_CHANNEL_ID)
    files_col.update_one({"_id": file_id}, {"$set": {"chat_id": DB_CHANNEL_ID, "msg_id": saved.id}}, upsert=True)
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

print("🩸 MADARA FILE SHARE BOT with MongoDB is summoning forbidden chakra...")
app.run()
