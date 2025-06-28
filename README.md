# ⚡ Madara Uchiha - File Share Bot

> Drop files like a shinobi, share like a legend 💀  
> This is a powerful Telegram bot to share any file using a unique private link.  
> Built for Termux warriors and Uchiha legends. 🩸

---

## 🔧 Features

- 📎 Upload any file and get a private, shareable link
- 🛡 Only allowed users can upload files
- 🔁 Permanent share link until file is deleted
- 🧑‍💻 Owner-only control panel with add/remove users
- 📣 Broadcast system to DM all users
- 💥 Built for Termux and small VPS

---

## ⚙️ Termux Installation (Step-by-Step)

### 🌀 1. Install Python and Git

```bash
pkg update && pkg upgrade -y
pkg install python git -y
pip install --upgrade pip
```

---

### 🌀 2. Clone the Bot

```bash
git clone https://github.com/cookies2002/file_share_bot
cd file_share_bot
```

---

### 🌀 3. Install Bot Requirements

```bash
pip install pyrogram tgcrypto python-dotenv
```

---

### 🌀 4. Create the `.env` File

Use any text editor like `nano`:

```bash
nano .env
```

Paste your credentials:

```
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
OWNER_IDS=123456789,987654321
```

> Replace with your real Telegram API ID, Hash, Bot Token from https://my.telegram.org and @BotFather  
> Use comma `,` to allow multiple owner IDs

---

### 🌀 5. Run the Bot

```bash
python bot.py
```

---

## ♻️ Keep the Bot Running Forever

### 🔮 Recommended: `tmux` Method (Madara-Style)

```bash
pkg install tmux -y
tmux new -s madara
python bot.py
```

✅ Now press: `Ctrl + B`, then `D` to detach  
▶️ To resume later: `tmux attach -t madara`

---

## 🧠 All Commands

### 👑 Owner-Only Commands:
| Command | Description |
|--------|-------------|
| `/addusers <user_id>` | Allow user to upload files |
| `/delusers <user_id>` | Remove user’s permission |
| `/getusers` | View allowed user list |
| `/broadcast <text>` | Send message to all saved users |
| `/help` | List all commands (for owners only) |

---

### 📎 File Sharing for Allowed Users:
- Send any file (photo/video/audio/doc)
- Bot replies with a unique private link
- File link format:  
  `https://t.me/your_bot_username?start=<file_id>`

---

## 🧾 Example `.env` Format

```env
API_ID=1234567
API_HASH=abc123def456gh789ijkl
BOT_TOKEN=123456:ABC-YourBotTokenHere
OWNER_IDS=123456789,987654321
```

---

## 👑 Style Signature

```
🩸 Madara Uchiha File Share Bot  
Born to destroy, not to please ⚔️  
```

---

## 🙏 Credits

- Original repo: https://github.com/cookies2002/file_share_bot
- Modded for Madara power by: @YourUsername