
<p align="center">
  <img src="https://upload.wikimedia.org/wikipedia/en/thumb/2/21/Madara_Uchiha.png/220px-Madara_Uchiha.png" height="150"/><br>
  <strong>𒆜 𝗠 𝗔 𝗗 𝗔 𝗥 𝗔 - 𝐅𝐢𝐥𝐞 𝐒𝐡𝐚𝐫𝐞 𝐁𝐨𝐭 ⚡</strong>
</p>

> A powerful File Share Bot created for Telegram, forged in the shadows by Madara Uchiha himself.  
> Store files secretly, retrieve them via sacred links.

---

## 🌀 Features

- 🔗 Generate shareable links for any file you send
- 🔒 Only the Uchiha clan (bot owner) can generate links
- 📥 Instant access to stored files via `/start` link
- 🛡 Termux supported for 24/7 battle-ready mode
- ⚙ No external DB required (pure JSON powered)

---

## 🧪 Deploy in Termux (Shadow VPS)

### ⚔ Prepare Your Phone

```bash
pkg update && pkg upgrade -y
pkg install python git -y
pip install pyrogram tgcrypto python-dotenv
pkg install tmux -y
```

### 🌀 Clone the Forbidden Repository

```bash
git clone https://github.com/cookies2002/file_share_bot
cd file_share_bot
```

### 🖋 Fill the `.env` Scroll

```env
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
OWNER_ID=your_telegram_id
```

Get values from [my.telegram.org](https://my.telegram.org) and @BotFather.

---

## 🔥 Start the Bot

```bash
python bot.py
```

---

## ♾️ Eternal Life: Keep Bot Running

Use **tmux** to keep the bot alive even if you leave:

```bash
tmux new -s madara
python bot.py
# To detach: Ctrl+B then D
# To re-attach: tmux attach -t madara
# To kill: tmux kill-session -t madara
```

Optional auto-start:

```bash
echo 'cd ~/file_share_bot && tmux new-session -d -s madara "python bot.py"' >> ~/.bashrc
```

---

## 🧿 Usage

- Forward any file
- Bot gives sacred link
- Share that link to reveal the secret

---

## 🐲 Made by Madara Uchiha

For any power-ups or alliance: [@Madara_Uchiha_lI](https://t.me/Madara_Uchiha_lI)
