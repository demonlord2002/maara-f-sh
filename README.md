# 📁 MADARA File Share Bot

This Telegram bot lets you upload and share files via a direct link.

## 🚀 Features
- Upload any file (document, video, image)
- Generate a shareable link
- Retrieve files from links
- Works on Termux, VPS, or Railway

## 🛠 Setup

### Termux / Local
1. Update and install Python:
   ```bash
   pkg update && pkg install python git
   pip install --upgrade pip
   ```

2. Clone the repo:
   ```bash
   git clone https://github.com/yourname/madara-file-share-bot.git
   cd madara-file-share-bot
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up `.env` file:
   ```bash
   cp .env.example .env
   ```

5. Run the bot:
   ```bash
   python bot.py
   ```

## ✨ Powered by [Pyrogram](https://docs.pyrogram.org)
