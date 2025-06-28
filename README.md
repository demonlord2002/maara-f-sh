# 🩸 Madara Uchiha File Share Bot

A Termux-ready Telegram bot to share files, generate private download links, and control upload permissions.

## 🔧 Features

- Send files and generate shareable links
- Add/remove allowed uploaders dynamically
- Broadcast messages to all users
- Simple `/start`, `/help`, `/addusers`, `/getusers`, etc.

## ⚙️ Setup

1. Clone the repo and edit `.env` file:

```
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
OWNER_IDS=123456789,987654321
```

2. Start the bot:

```bash
pip install pyrogram tgcrypto python-dotenv
python bot.py
```

## 🧠 Commands

- `/start` — Start bot or fetch shared file
- `/help` — Show all commands (owner only)
- `/addusers <id>` — Allow a user to upload files
- `/delusers <id>` — Remove permission from user
- `/getusers` — View allowed users (clickable IDs)
- `/broadcast <text>` — Send message to all

## 👑 Powered by Madara Uchiha

> “Born to destroy, not to please.” ⚔️