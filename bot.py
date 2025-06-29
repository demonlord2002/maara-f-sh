# Madara Uchiha File Share Bot with 28-Day Expiry Feature

from pyrogram import Client, filters
from pyrogram.types import Message
import os, json, time
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_IDS = list(map(int, os.getenv("OWNER_IDS").split(",")))

DB_FILE = "db.json"
USERS_FILE = "users.json"

for file in [DB_FILE, USERS_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({} if file == DB_FILE else {}, f)

with open(DB_FILE, "r") as f:
    db = json.load(f)
with open(USERS_FILE, "r") as f:
    allowed_users = json.load(f)

app = Client("madara_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def is_active(user_id):
    expiry = allowed_users.get(str(user_id))
    if not expiry:
        return False
    return time.time() < expiry

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    user_id = message.from_user.id
    if not is_active(user_id):
        await message.reply(
            "❌ You dare challenge Madara Uchiha's forbidden uploader?\n\n"
            "⚠️ This bot is sealed for chosen users only.\n"
            "🧿 Plan: 28 days for ₹50\n"
            "👁‍🗨 Contact the ghost of the Akatsuki ➔ @Madara_Uchiha_lI"
        )
        return

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
            "Send me any file and I will return a private sharing link.\n"
            "Only chosen shinobi can access the vault.\n"
            "Use /status to check your remaining time."
        )

@app.on_message(filters.command("status") & filters.private)
async def status_cmd(client, message: Message):
    user_id = message.from_user.id
    expiry = allowed_users.get(str(user_id))
    if not expiry:
        await message.reply("❌ You are not authorized.\nContact @Madara_Uchiha_lI to activate your plan.")
        return
    remaining = expiry - time.time()
    if remaining <= 0:
        await message.reply("⛔ Your plan has expired.\nContact @Madara_Uchiha_lI to renew it.")
    else:
        days = int(remaining // 86400)
        hours = int((remaining % 86400) // 3600)
        minutes = int((remaining % 3600) // 60)
        await message.reply(f"✅ You are authorized.\nTime left: {days} days, {hours} hours, {minutes} minutes")

@app.on_message(filters.command("addusers") & filters.private)
async def add_user(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only owners can add users.")
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("⚠️ Usage: /addusers <telegram_user_id>")
    
    new_user = parts[1]
    expiry_time = time.time() + 28 * 86400
    allowed_users[new_user] = expiry_time
    with open(USERS_FILE, "w") as f:
        json.dump(allowed_users, f)
    await message.reply(f"✅ User `{new_user}` added with 28 days access.")

@app.on_message(filters.command("delusers") & filters.private)
async def del_user(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only owners can remove users.")
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("⚠️ Usage: /delusers <telegram_user_id>")

    del_user = parts[1]
    if del_user not in allowed_users:
        return await message.reply("ℹ️ User not found in allowed list.")
    del allowed_users[del_user]
    with open(USERS_FILE, "w") as f:
        json.dump(allowed_users, f)
    await message.reply(f"✅ User `{del_user}` removed from access.")

@app.on_message(filters.command("getusers") & filters.private)
async def get_users(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only owners can use this command.")
    if not allowed_users:
        return await message.reply("⚠️ No users have been added yet.")
    user_list = "**👤 Allowed Users List:**\n\n"
    for uid in allowed_users:
        user_list += f"- `{uid}` → [Link](https://t.me/user?id={uid})\n"
    await message.reply(user_list, disable_web_page_preview=True)

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only owners can use the /help command.")
    await message.reply(
        "**🛠 Madara Uchiha Bot Commands:**\n\n"
        "🔹 /addusers <id> — Give 28-day access\n"
        "🔹 /delusers <id> — Remove access\n"
        "🔹 /getusers — List allowed users\n"
        "🔹 /broadcast <msg> — Message all users\n"
        "🔹 /status — Show your plan expiry"
    )

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_handler(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ You are not allowed to use this command.")

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply("❗ Use:\n`/broadcast Your message here`")

    sent, failed = 0, 0
    for user_id in allowed_users:
        try:
            await client.send_message(int(user_id), parts[1])
            sent += 1
        except:
            failed += 1

    await message.reply(f"📢 Broadcast done.\n✅ Sent: {sent}\n❌ Failed: {failed}")

@app.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def save_file(client, message: Message):
    user_id = message.from_user.id
    if not is_active(user_id):
        return await message.reply("🚫 You're not allowed to upload files. Plan expired or not activated.")

    file_id = str(message.id)
    db[file_id] = {"chat_id": message.chat.id, "msg_id": message.id}
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

    bot_username = (await app.get_me()).username
    link = f"https://t.me/{bot_username}?start={file_id}"
    await message.reply(f"✅ File saved!\n📎 Link: {link}")

print("✅ MADARA FILE SHARE BOT with PLAN is running...")
app.run()
