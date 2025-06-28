# 📁 Telegram File Share Bot

A simple Telegram bot that stores forwarded files and generates shareable links that anyone can use to download them. Powered by Pyrogram and easily deployable on Heroku.

---

## 🚀 Deploy to Heroku

Click the button below to deploy this bot to **Heroku** in one click:

<p align="center">
  <a href="https://heroku.com/deploy?template=https://github.com/cookies2002/file_share_bot">
    <img src="https://img.shields.io/badge/Deploy%20To%20Heroku-purple?style=for-the-badge&logo=heroku"/>
  </a>
</p>

---

## ⚙️ Features

- 🔐 Owner-only file sharing
- 🔗 Share any Telegram file through a unique URL
- 💾 Files are stored in a private channel
- 🎯 Only bot owner can generate share links
- 📬 Supports media files of all types
- 🗑️ Automatically deletes expired or old file references (optional)

---

## 🧩 Environment Variables

| Variable        | Description                                      |
|-----------------|--------------------------------------------------|
| `BOT_TOKEN`     | Your bot token from [@BotFather](https://t.me/BotFather) |
| `API_ID`        | Telegram API ID from [my.telegram.org](https://my.telegram.org) |
| `API_HASH`      | Telegram API Hash from [my.telegram.org](https://my.telegram.org) |
| `OWNER_ID`      | Your Telegram user ID (get it via @userinfobot)  |
| `CHANNEL_ID`    | ID of your private storage channel (bot must be admin) |

---

## 💻 Run Locally (Advanced)

```bash
git clone https://github.com/cookies2002/file_share_bot
cd file_share_bot

# Install dependencies
pip3 install -r requirements.txt

# Set environment variables (can use dotenv or export manually)
export BOT_TOKEN="YOUR_BOT_TOKEN"
export API_ID=123456
export API_HASH="your_api_hash"
export OWNER_ID=123456789
export CHANNEL_ID=-100xxxxxxxxx

# Run the bot
python3 bot.py
