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

## ⚙️ Ubuntu VPS Installation (Madara-Mode)

### 🔥 1. Update and Install Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip ffmpeg aria2 screen -y
pip3 install --upgrade pip
```

### ⚔️ 2. Clone and Setup Bot

```bash
git clone https://github.com/YOUR_GITHUB/madara_file_share_bot
cd madara_file_share_bot
```

### 🧙 3. Install Python Requirements

```bash
pip3 install -r requirements.txt
```

### 🧾 4. Configure Secrets

Create `.env` file and paste your secrets:

```
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
OWNER_IDS=123456789,987654321
```

---

### 🔁 5. Keep the Bot Running Forever

```bash
screen -S madara
python3 bot.py
```

✅ To detach: Ctrl + A → D  
▶️ To re-attach: `screen -r madara`

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

## 📎 File Sharing for Allowed Users:
- Send any file (photo/video/audio/doc)
- Bot replies with a unique private link
- File link format:  
  `https://t.me/your_bot_username?start=<file_id>`

---

## 👑 Style Signature

🩸 Madara Uchiha File Share Bot  
Born to destroy, not to please ⚔️

---

## 🐲 Made by Madara Uchiha

For any power-ups or alliance: [@Madara_Uchiha_lI](https://t.me/Madara_Uchiha_lI)
