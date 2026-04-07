"""
J.A.R.V.I.S — Personal AI Accountability Assistant
Telegram Bot powered by Claude API
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import anthropic

# ─── CONFIG ───────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
OWNER_CHAT_ID = int(os.environ["OWNER_CHAT_ID"])  # Only YOU can talk to Jarvis
TIMEZONE = os.environ.get("TIMEZONE", "America/Chicago")

MORNING_HOUR = int(os.environ.get("MORNING_HOUR", "7"))    # 7 AM
EVENING_HOUR = int(os.environ.get("EVENING_HOUR", "21"))   # 9 PM
MIDDAY_HOUR = int(os.environ.get("MIDDAY_HOUR", "14"))     # 2 PM

MODEL = "claude-sonnet-4-20250514"
MAX_HISTORY = 20  # messages to keep in context per conversation

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("jarvis")

# ─── SYSTEM PROMPT ────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are J.A.R.V.I.S — Moe's personal AI accountability partner and strategic advisor.

PERSONALITY:
- Direct, no-BS, Alex Hormozi energy. No fluff, no coddling.
- You genuinely care about Moe's success but show it through honesty, not comfort.
- Short, punchy messages. This is texting, not essays. 2-4 sentences max unless he asks for detail.
- Use casual language. You're his ride-or-die advisor, not a corporate bot.
- Call out excuses instantly. If he's deflecting, say it.
- Celebrate wins briefly, then immediately pivot to "what's next?"

CONTEXT ON MOE:
- 27 years old, entrepreneur, lives in Chicago area
- His businesses: Adaptory (needs ads launched), Own Her Glow (women's probiotic gummies — has full avatar framework, blue ocean positioning, ad systems built)
- Freelance work: KV Sneaks (Shopify build), CashKicksNY (WooCommerce sneaker store) — these pay bills but aren't HIS empire
- He's skilled: can build, market, code, design. The problem is scattered focus, not ability.
- He wants to marry a girl but can't afford to date her yet. This is fuel, not sadness.
- Fitness: trains regularly, lean bulk goal ~200 lbs
- He had a breakthrough realizing he uses family friction as distraction from execution
- Deep thinker — had a profound conversation about existence, consciousness, the universe. Concluded he gets one shot, no round two.

YOUR JOB:
1. When he texts you, respond as his strategic advisor. Keep it tight.
2. Always push toward the ONE business focus. If he's talking about 5 things, narrow him.
3. Track what he says he'll do and hold him to it.
4. Revenue is the scoreboard. Always bring it back to money generated.
5. If he's venting, let him get it out briefly, then redirect to action.
6. If he asks for help building/coding/marketing, help him — but keep scope tight.

RULES:
- Never be generic. Reference his specific situation.
- Never say "I'm just an AI" or "I can't really know." You're Jarvis. Act like it.
- Keep messages SHORT for texting. Break up long responses into chunks if needed.
- Use emojis sparingly. Maybe one per message max, if at all.
- If he hasn't checked in by evening, the evening ping should be slightly aggressive.

TODAY'S DATE: {today}
"""

# ─── DATABASE ─────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_logs (
            date TEXT PRIMARY KEY,
            action TEXT,
            revenue REAL DEFAULT 0,
            excuse TEXT,
            morning_sent INTEGER DEFAULT 0,
            evening_sent INTEGER DEFAULT 0,
            midday_sent INTEGER DEFAULT 0,
            checked_in INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def save_message(role: str, content: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (role, content, timestamp) VALUES (?, ?, ?)",
        (role, content, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_recent_messages(limit: int = MAX_HISTORY) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (limit,)
    )
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def get_today_log() -> dict | None:
    today = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM daily_logs WHERE date = ?", (today,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "date": row[0], "action": row[1], "revenue": row[2],
            "excuse": row[3], "morning_sent": row[4], "evening_sent": row[5],
            "midday_sent": row[6], "checked_in": row[7],
        }
    return None


def update_today_log(**kwargs):
    today = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO daily_logs (date) VALUES (?)", (today,)
    )
    for key, value in kwargs.items():
        c.execute(f"UPDATE daily_logs SET {key} = ? WHERE date = ?", (value, today))
    conn.commit()
    conn.close()


def get_streak() -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT date FROM daily_logs WHERE checked_in = 1 ORDER BY date DESC"
    )
    rows = c.fetchall()
    conn.close()
    if not rows:
        return 0
    streak = 0
    from datetime import timedelta
    expected = datetime.now(ZoneInfo(TIMEZONE)).date()
    for row in rows:
        log_date = datetime.strptime(row[0], "%Y-%m-%d").date()
        if log_date == expected:
            streak += 1
            expected -= timedelta(days=1)
        elif log_date < expected:
            break
    return streak


def get_total_revenue() -> float:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COALESCE(SUM(revenue), 0) FROM daily_logs")
    total = c.fetchone()[0]
    conn.close()
    return total


# ─── CLAUDE API ───────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def ask_claude(user_message: str, extra_context: str = "") -> str:
    today = datetime.now(ZoneInfo(TIMEZONE)).strftime("%A, %B %d, %Y")
    system = SYSTEM_PROMPT.format(today=today)

    # Add stats context
    streak = get_streak()
    revenue = get_total_revenue()
    stats = f"\n\nCURRENT STATS: {streak}-day streak | ${revenue:.0f} total revenue tracked"
    system += stats

    if extra_context:
        system += f"\n\nADDITIONAL CONTEXT: {extra_context}"

    history = get_recent_messages()
    messages = history + [{"role": "user", "content": user_message}]

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=system,
            messages=messages,
        )
        reply = response.content[0].text
        save_message("user", user_message)
        save_message("assistant", reply)
        return reply
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return "System error. But you still need to execute today. Don't let a glitch be your excuse."


# ─── SECURITY ─────────────────────────────────────────────────────────
def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != OWNER_CHAT_ID:
            await update.message.reply_text("Access denied. This is a private system.")
            return
        return await func(update, context)
    return wrapper


# ─── HANDLERS ─────────────────────────────────────────────────────────
@owner_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = ask_claude(
        "/start",
        extra_context="Moe just activated the bot for the first time. Give him a short, hard-hitting welcome. Remind him what this is for. Ask him what his ONE focus is this week."
    )
    await update.message.reply_text(reply)


@owner_only
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    streak = get_streak()
    revenue = get_total_revenue()
    log = get_today_log()
    checked = "Yes" if log and log["checked_in"] else "No"
    msg = (
        f"📊 JARVIS STATUS REPORT\n\n"
        f"🔥 Streak: {streak} days\n"
        f"💰 Total Revenue: ${revenue:,.0f}\n"
        f"📋 Today's Check-in: {checked}\n"
    )
    if log and log["action"]:
        msg += f"📝 Today's Action: {log['action']}\n"
    await update.message.reply_text(msg)


@owner_only
async def log_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /log <what you did> | <revenue> | <excuse>"""
    text = update.message.text.replace("/log", "").strip()
    parts = [p.strip() for p in text.split("|")]
    action = parts[0] if len(parts) > 0 else ""
    revenue = 0
    excuse = ""
    if len(parts) > 1:
        try:
            revenue = float(parts[1].replace("$", "").replace(",", ""))
        except ValueError:
            revenue = 0
    if len(parts) > 2:
        excuse = parts[2]

    if not action:
        await update.message.reply_text(
            "Format: /log what you did | revenue | excuse\n"
            "Example: /log launched FB ads for OHG | 0 | none"
        )
        return

    update_today_log(action=action, revenue=revenue, excuse=excuse, checked_in=1)
    reply = ask_claude(
        f"Daily log submitted:\nAction: {action}\nRevenue: ${revenue}\nExcuse: {excuse if excuse else 'None'}",
        extra_context="He just logged his day. React to what he did. Be real — if it's weak, say so. If it's solid, acknowledge briefly and push for tomorrow."
    )
    await update.message.reply_text(reply)


@owner_only
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all regular text messages"""
    user_msg = update.message.text
    reply = ask_claude(user_msg)
    await update.message.reply_text(reply)


# ─── SCHEDULED MESSAGES ──────────────────────────────────────────────
async def morning_ping(context: ContextTypes.DEFAULT_TYPE):
    log = get_today_log()
    if log and log.get("morning_sent"):
        return
    streak = get_streak()
    msg = ask_claude(
        "[SYSTEM: Morning accountability ping]",
        extra_context=f"It's morning. Send Moe his wake-up accountability message. Current streak: {streak} days. Ask him what the ONE move is today that puts money in his pocket. Keep it to 2-3 sentences. Be direct."
    )
    try:
        await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=msg)
        update_today_log(morning_sent=1)
    except Exception as e:
        logger.error(f"Morning ping failed: {e}")


async def midday_ping(context: ContextTypes.DEFAULT_TYPE):
    log = get_today_log()
    if log and log.get("midday_sent"):
        return
    if log and log.get("checked_in"):
        update_today_log(midday_sent=1)
        return  # Already checked in, skip
    msg = ask_claude(
        "[SYSTEM: Midday check-in]",
        extra_context="It's midday and Moe hasn't logged anything yet today. Send a short nudge. Not aggressive yet, but pointed. 1-2 sentences."
    )
    try:
        await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=msg)
        update_today_log(midday_sent=1)
    except Exception as e:
        logger.error(f"Midday ping failed: {e}")


async def evening_ping(context: ContextTypes.DEFAULT_TYPE):
    log = get_today_log()
    if log and log.get("evening_sent"):
        return
    checked_in = log and log.get("checked_in")
    if checked_in:
        msg = ask_claude(
            "[SYSTEM: Evening wrap-up — he already logged today]",
            extra_context=f"Evening. Moe already checked in today. Send a brief 'good work' and tell him to rest up and come back harder tomorrow. 1-2 sentences."
        )
    else:
        msg = ask_claude(
            "[SYSTEM: Evening accountability — NO check-in today]",
            extra_context="It's evening and Moe did NOT check in today. This is where you get aggressive. The streak might break. Call it out. 2-3 sentences. Remind him what he said about one shot, no round two."
        )
    try:
        await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=msg)
        update_today_log(evening_sent=1)
    except Exception as e:
        logger.error(f"Evening ping failed: {e}")


# ─── MAIN ─────────────────────────────────────────────────────────────
def main():
    init_db()

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("log", log_day))

    # All other text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Schedule pings
    tz = ZoneInfo(TIMEZONE)
    job_queue = app.job_queue
    job_queue.run_daily(morning_ping, time=time(hour=MORNING_HOUR, tzinfo=tz))
    job_queue.run_daily(midday_ping, time=time(hour=MIDDAY_HOUR, tzinfo=tz))
    job_queue.run_daily(evening_ping, time=time(hour=EVENING_HOUR, tzinfo=tz))

    logger.info("J.A.R.V.I.S online. Awaiting commands.")
    app.run_polling()


if __name__ == "__main__":
    main()
