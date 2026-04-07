# J.A.R.V.I.S — Personal AI Accountability Bot

Your personal Jarvis. Claude-powered. Texts you daily. Holds you accountable. No mercy.

---

## What It Does

- **You text it anytime** → It responds as your strategic advisor with full context on your businesses, goals, and situation
- **7 AM** → Morning ping: "What's the ONE move today?"
- **2 PM** → Midday nudge if you haven't checked in
- **9 PM** → Evening report. If you logged your day, brief props. If you didn't, it gets aggressive.
- **Streak tracking** → Consecutive days of check-ins
- **Revenue tracking** → Running total of money YOUR businesses made

---

## Setup (30 minutes)

### Step 1: Create Your Telegram Bot

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Name it whatever you want (e.g., "JARVIS")
4. BotFather gives you a **token** — save it. Looks like: `7123456789:AAH...`

### Step 2: Get Your Chat ID

1. Search for **@userinfobot** on Telegram
2. Send it any message
3. It replies with your **Chat ID** — save it. It's a number like `123456789`

### Step 3: Get Your Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an API key
3. Add some credits ($5-10 is plenty to start — each message costs ~$0.01)

### Step 4: Set Up a Server

**Cheapest option: [Railway.app](https://railway.app)** (free tier available)

1. Push this folder to a GitHub repo
2. Connect Railway to the repo
3. Add these environment variables in Railway dashboard:

```
TELEGRAM_TOKEN=your_bot_token_here
ANTHROPIC_API_KEY=your_anthropic_key_here
OWNER_CHAT_ID=your_chat_id_here
TIMEZONE=America/Chicago
MORNING_HOUR=7
EVENING_HOUR=21
MIDDAY_HOUR=14
```

4. Deploy. Done.

**Alternative: Any VPS ($5/month DigitalOcean, Hetzner, etc.)**

```bash
# SSH into your server
git clone your-repo-url
cd jarvis-bot
pip install -r requirements.txt

# Set environment variables
export TELEGRAM_TOKEN="your_token"
export ANTHROPIC_API_KEY="your_key"
export OWNER_CHAT_ID="your_chat_id"
export TIMEZONE="America/Chicago"

# Run it
python jarvis_bot.py

# To keep it running after you close terminal:
nohup python jarvis_bot.py &
# Or better, use screen/tmux/systemd
```

---

## Commands

| Command | What it does |
|---------|-------------|
| `/start` | Boot up Jarvis, get your welcome message |
| `/status` | See your streak, revenue, today's check-in status |
| `/log did X \| $revenue \| excuse` | Log your day |

### Log Examples:
```
/log launched Meta ads for OHG | 0 | none
/log built landing page, 2 sales came in | 150 | got distracted for an hour on youtube
/log nothing productive | 0 | told myself I'd start after lunch and never did
```

### Or Just Text It:
You can text Jarvis anything — strategy questions, venting, brainstorming. It responds as your advisor with full context on who you are and what you're building.

---

## Customize

**Change scheduled times:** Update MORNING_HOUR, MIDDAY_HOUR, EVENING_HOUR env vars (24h format)

**Change personality:** Edit `SYSTEM_PROMPT` in jarvis_bot.py

**Change the context:** Update the "CONTEXT ON MOE" section in the system prompt as your situation evolves

---

## Cost

- **Telegram:** Free
- **Claude API:** ~$0.01 per message + ~$0.03/day for scheduled pings ≈ **$1-5/month**
- **Server:** Free (Railway) or $5/month (VPS)

**Total: $1-10/month for a personal AI that holds you accountable 24/7.**
