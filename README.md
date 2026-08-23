# Valorant Esports Discord Bot

A Discord bot that automatically posts **Valorant esports news**, **live match scores with player stats**, **upcoming matches**, and **completed results** to channels you assign.

Data comes from [vlr.gg](https://www.vlr.gg) via the unofficial [vlrggapi](https://github.com/axsddlr/vlrggapi).

---

## What the bot does

| Feature | Channel | Update frequency |
|--------|---------|------------------|
| News articles | `#vct-news` | Every 1 hour |
| Live scores + player stats | `#vct-live` | Every 80 sec |
| Upcoming matches | `#vct-upcoming` | Every 2 hours |
| Completed results | `#vct-results` | Every 6 hours |

Live match messages **edit in place** so your channel doesn't get spammed.

---

## What YOU need to do (step by step)

### 1. Create a Discord bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application** → give it a name (e.g. "Valorant Esports")
3. Open **Bot** in the sidebar → **Reset Token** → copy the token (keep it secret)
4. Under **Privileged Gateway Intents**, you do **not** need Message Content Intent for this bot
5. Open **OAuth2 → URL Generator**
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Embed Links`, `Read Message History`, `View Channels`
6. Copy the generated URL, open it in your browser, and **invite the bot to your server**

### 2. Self-host the VLR API (required)

The public API (`https://vlrggapi.vercel.app`) is currently **down**. You must run it locally:

```bash
# In a separate terminal/folder
git clone https://github.com/axsddlr/vlrggapi.git
cd vlrggapi
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

The API runs at **http://127.0.0.1:3001**. Verify:

```bash
curl http://127.0.0.1:3001/v2/health
curl http://127.0.0.1:3001/v2/news
```

Keep this running whenever the Discord bot is running.

> **Deploying 24/7:** Run both the API and bot on a VPS, Railway, Render, or your PC. If you host the API elsewhere, set `VLR_API_BASE` in `.env` to that URL.

### 3. Set up the Discord bot

```bash
cd "/Users/ujjwal18/Desktop/discord bot "
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```env
DISCORD_TOKEN=paste_your_bot_token_here
VLR_API_BASE=http://127.0.0.1:3001
```

### 4. Run the bot

```bash
python bot.py
```

You should see: `Logged in as YourBot#1234`

### 5. Create Discord channels

Under your **VCT** category, create four text channels:

```
📁 VCT
   ├── #vct-news       ← news articles
   ├── #vct-live       ← live scores + player stats
   ├── #vct-upcoming   ← scheduled matches
   └── #vct-results    ← completed matches
```

Set **@everyone → Deny Send Messages** on each channel so only the bot can post.

### 6. Configure channels in Discord

In your server, run:

```
/setup news_channel:#vct-news live_channel:#vct-live upcoming_channel:#vct-upcoming results_channel:#vct-results
```

Pick the channels where posts should go. The bot needs **Send Messages** and **Embed Links** in both.

Check everything with:

```
/status
```

Optional admin test commands:

```
/test-news
/test-matches
```

---

## Slash commands

| Command | Who | Description |
|---------|-----|-------------|
| `/setup` | Anyone | Assign news, live, upcoming, and results channels |
| `/status` | Anyone | Check API + channel config |
| `/test-news` | Manage Server | Post latest news once |
| `/test-matches` | Manage Server | Post sample live/upcoming matches |

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_TOKEN` | — | **Required.** Bot token from Developer Portal |
| `VLR_API_BASE` | `http://127.0.0.1:3001` | vlrggapi base URL |
| `NEWS_POLL_INTERVAL` | `3600` (1 hr) | Seconds between news checks |
| `LIVE_POLL_INTERVAL` | `80` | Seconds between live score updates |
| `UPCOMING_POLL_INTERVAL` | `7200` (2 hr) | Seconds between upcoming match checks |
| `RESULTS_POLL_INTERVAL` | `21600` (6 hr) | Seconds between completed result checks |

---

## Project structure

```
discord bot/
├── bot.py           # Main bot + background tasks
├── vlr_client.py    # vlrggapi HTTP client
├── embeds.py        # Discord embed formatting
├── storage.py       # Per-server config (data/guilds.json)
├── config.py        # Environment settings
├── requirements.txt
├── .env.example
└── README.md
```

---

## Troubleshooting

**Bot online but no posts**
- Run `/status` — is the VLR API healthy?
- Did you run `/setup` with valid channels?
- Is vlrggapi running on the URL in `.env`?

**`/status` shows API error**
- Start vlrggapi: `python main.py` inside the vlrggapi folder
- Confirm: `curl http://127.0.0.1:3001/v2/health`

**Slash commands don't appear**
- Wait up to 1 hour for global sync, or kick/re-invite the bot
- Ensure you invited with `applications.commands` scope

**Live player stats missing**
- Player stats come from match details; they appear once the match has map data on vlr.gg
- Early in a map, stats may be limited until rounds are played

**Duplicate upcoming/result posts after restart**
- The bot tracks posted items in `data/guilds.json`. Don't delete that file unless you want reposts.

---

## Running 24/7 (optional)

**macOS/Linux with `screen` or `tmux`:**

```bash
# Terminal 1 — API
cd vlrggapi && source .venv/bin/activate && python main.py

# Terminal 2 — Bot
cd "discord bot " && source .venv/bin/activate && python bot.py
```

For production, use a process manager (`systemd`, `pm2`, Docker) or a cloud host.

---

## License

Bot code: use freely. vlrggapi is MIT licensed — see [vlrggapi repo](https://github.com/axsddlr/vlrggapi).
