import os
import re
import asyncio
import logging
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)

# Bot configuration
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
DB_CHANNEL_ID = os.getenv("DB_CHANNEL_ID")

# MongoDB setup
client = MongoClient(MONGO_URI)
db = client["file_share"]
users_col = db["users"]

# Pyrogram client
app = Client("file_share_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Store user batch state
user_batch_state = {}

# --------------------------- Utility Functions --------------------------- #

def is_active(user_id):
    return users_col.find_one({"user_id": user_id}) is not None

def get_all_users():
    return [user["user_id"] for user in users_col.find()]

# --------------------------- Command Handlers --------------------------- #

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    user_id = message.from_user.id
    if not is_active(user_id):
        return await message.reply("❌ You're not an authorized user.")

    args = message.command
    if len(args) > 1 and args[1].startswith("batch_"):
        try:
            _, first_msg_id, last_msg_id = args[1].split("_")
            first_msg_id = int(first_msg_id)
            last_msg_id = int(last_msg_id)

            msg_ids = range(first_msg_id, last_msg_id + 1)
            for msg_id in msg_ids:
                await client.copy_message(
                    chat_id=message.chat.id,
                    from_chat_id=DB_CHANNEL_ID,
                    message_id=msg_id
                )
            return
        except Exception as e:
            logging.error(f"Error in /start batch handler: {e}")
            return await message.reply("❌ File not found or expired. This message only gets the bot, not the file 🗃️ 🥺")

    await message.reply("👋 Welcome to Madara File Share Bot! Send me any file to generate a sharable link.")

@app.on_message(filters.command("batch") & filters.private)
async def batch_cmd(client, message: Message):
    if not is_active(message.from_user.id):
        return await message.reply("🚫 Plan expired. Contact @Madara_Uchiha_lI")

    user_id = message.from_user.id
    user_batch_state[user_id] = {"step": "first_link"}

    await message.reply("📥 Give me the **first message link** from your batch channel.")

@app.on_message(filters.text & filters.private)
async def handle_batch_links(client, message: Message):
    user_id = message.from_user.id
    state = user_batch_state.get(user_id)

    if not state:
        return

    if state["step"] == "first_link":
        match_first = re.search(r"t\.me/c/(\d+)/(\d+)", message.text)
        if not match_first:
            return await message.reply("❌ Invalid first link format. Use t.me/c/...")

        state["chat_id"] = int(match_first.group(1))
        state["first_msg_id"] = int(match_first.group(2))
        state["step"] = "last_link"

        await message.reply("📥 Now give me the **last message link** from your batch channel.")

    elif state["step"] == "last_link":
        match_last = re.search(r"t\.me/c/(\d+)/(\d+)", message.text)
        if not match_last:
            return await message.reply("❌ Invalid last link format. Use t.me/c/...")

        last_msg_id = int(match_last.group(2))
        first_msg_id = state["first_msg_id"]

        if last_msg_id < first_msg_id:
            return await message.reply("❌ Last message ID cannot be smaller than first message ID.")

        bot_username = "Madara_FSBot"
        batch_link = f"https://t.me/{bot_username}?start=batch_{first_msg_id}_{last_msg_id}"

        user_batch_state.pop(user_id)

        await message.reply(
            f"✅ Batch created successfully!\n📎 Link: {batch_link}",
            disable_web_page_preview=True
        )

@app.on_message(filters.command("addusers") & filters.user(123456789))  # Replace with admin ID
async def add_user(client, message: Message):
    if len(message.command) != 2:
        return await message.reply("Usage: /addusers <user_id>")

    user_id = int(message.command[1])
    users_col.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)
    await message.reply("✅ User added.")

@app.on_message(filters.command("delusers") & filters.user(123456789))
async def del_user(client, message: Message):
    if len(message.command) != 2:
        return await message.reply("Usage: /delusers <user_id>")

    user_id = int(message.command[1])
    users_col.delete_one({"user_id": user_id})
    await message.reply("🗑️ User removed.")

@app.on_message(filters.command("getusers") & filters.user(123456789))
async def get_users(client, message: Message):
    user_list = get_all_users()
    await message.reply("👥 Authorized users:\n" + "\n".join([str(u) for u in user_list]))

@app.on_message(filters.document | filters.video | filters.audio | filters.photo)
async def save_file(client, message: Message):
    if not is_active(message.from_user.id):
        return await message.reply("❌ You're not an authorized user.")

    forwarded = await message.forward(DB_CHANNEL_ID)
    file_id = forwarded.message_id
    bot_username = "SunsetOfMe"
    share_link = f"https://t.me/{bot_username}?start={file_id}"

    await message.reply(
        f"✅ File saved successfully!\n📎 Link: {share_link}",
        disable_web_page_preview=True
    )

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message: Message):
    await message.reply("""
🤖 **Madara File Share Bot Help**

📤 Send me any file (video, doc, etc.) to get a sharable link.
🔗 Use /batch to generate a link for multiple posts.

🧑‍💻 Admin Commands:
/addusers <user_id>
/delusers <user_id>
/getusers
/broadcast <message>
""")

# --------------------------- Bot Start --------------------------- #

print("🩸 MADARA FILE SHARE BOT with MongoDB is summoning forbidden chakra...")
app.run()
