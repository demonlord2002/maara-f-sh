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
USERS_FILE = "users.json"

# Ensure files exist
for file in [DB_FILE, USERS_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({} if file == DB_FILE else [], f)

# Load data
with open(DB_FILE, "r") as f:
    db = json.load(f)
with open(USERS_FILE, "r") as f:
    allowed_users = json.load(f)

app = Client("madara_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    user_id = message.from_user.id

    # 🔐 If not allowed, block with attitude
    if user_id not in OWNER_IDS and user_id not in allowed_users:
        return await message.reply(
            "❌ You dare challenge Madara Uchiha's forbidden uploader?\n\n"
            "🚷 You are *not allowed* to enter this file-sharing jutsu.\n"
            "🔗 Want to upload or share files?\n"
            "👁‍🔦 DM the Ghost of the Akatsuki ➜ @Madara_Uchiha_lI"
        )

    # If file ID in link
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
        # Authorized welcome
        await message.reply(
            "**🔥 Welcome to Madara's Secret File Vault 🔥**\n\n"
            "📥 Drop any file. You’ll get a private share link instantly.\n"
            "🩸 Only chosen ones can upload into this forbidden space.\n\n"
            "Use /help to view Uchiha scrolls 📜"
        )


@app.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only owners can use the help command.")

    await message.reply(
        "**🛠 Madara Uchiha Bot Commands:**\n\n"
        "🔹 /start — Start or get file by link\n"
        "🔹 /help — Show all available commands\n"
        "🔹 /broadcast <text> — Send message to all users\n"
        "🔹 /addusers <id> — Allow user to upload files\n"
        "🔹 /delusers <id> — Remove user access\n"
        "🔹 /getusers — List all allowed users"
    )


@app.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def save_file(client, message: Message):
    user_id = message.from_user.id
    if user_id not in OWNER_IDS and user_id not in allowed_users:
        return await message.reply("🚫 You're not allowed to upload files.")

    file_id = str(message.id)
    db[file_id] = {"chat_id": message.chat.id, "msg_id": message.id}
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

    bot_username = (await app.get_me()).username
    link = f"https://t.me/{bot_username}?start={file_id}"
    await message.reply(f"✅ File saved!\n📎 Link: {link}")


@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_handler(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only owners can broadcast.")

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply("❗ Usage: /broadcast <message>")

    sent, failed = 0, 0
    for file_info in db.values():
        try:
            await client.send_message(file_info["chat_id"], parts[1])
            sent += 1
        except:
            failed += 1

    await message.reply(f"📢 Broadcast done.\n✅ Sent: {sent}\n❌ Failed: {failed}")


@app.on_message(filters.command("addusers") & filters.private)
async def add_user(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only owners can add users.")
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("⚠️ Usage: /addusers <telegram_user_id>")

    new_user = int(parts[1])
    if new_user in allowed_users:
        return await message.reply("ℹ️ User already has access.")
    allowed_users.append(new_user)
    with open(USERS_FILE, "w") as f:
        json.dump(allowed_users, f)
    await message.reply(f"✅ User `{new_user}` added.")


@app.on_message(filters.command("delusers") & filters.private)
async def del_user(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only owners can remove users.")
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("⚠️ Usage: /delusers <telegram_user_id>")

    del_user = int(parts[1])
    if del_user not in allowed_users:
        return await message.reply("ℹ️ User not found in allowed list.")
    allowed_users.remove(del_user)
    with open(USERS_FILE, "w") as f:
        json.dump(allowed_users, f)
    await message.reply(f"✅ User `{del_user}` removed.")


@app.on_message(filters.command("getusers") & filters.private)
async def get_users(client, message: Message):
    if message.from_user.id not in OWNER_IDS:
        return await message.reply("❌ Only owners can use this command.")
    if not allowed_users:
        return await message.reply("⚠️ No users have been added yet.")
    user_list = "**👤 Allowed Users List:**\n\n"
    for uid in allowed_users:
        user_list += f"- [`{uid}`](https://t.me/user?id={uid})\n"
    await message.reply(user_list, disable_web_page_preview=True)


print("✅ MADARA FILE SHARE BOT is running...")
app.run()
