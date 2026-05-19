"""
RandAI Scraper Bot (@RandAI_bot)
Author: lck920
GitHub: https://github.com/lck920/randai-scraper-bot

Purpose:
- Scrape Sports Toto and Magnum 4D results from 4dmoon
- Update local CSV datasets
- Notify subscribed Telegram users
- Support hot/cold number analysis
- Search old results
- Daily statistics
- Auto GitHub backup
- Optional voice meme replies

Security:
- Bot token and admin chat ID are NOT hardcoded.
- Set them using environment variables:
    RAND_AI_BOT_TOKEN
    RAND_AI_ADMIN_CHAT_ID
"""

import os
import re
import csv
import sys
import json
import glob
import random
import subprocess
from collections import Counter
from datetime import datetime, time
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_NAME = "@RandAI_bot"
GITHUB_REPO_URL = "https://github.com/lck920/randai-scraper-bot"

BOT_TOKEN = os.getenv("RAND_AI_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("RAND_AI_ADMIN_CHAT_ID")
ADMIN_CHAT_ID = int(ADMIN_CHAT_ID) if ADMIN_CHAT_ID else None

SCRAPER_FILES = ["scrape_toto.py", "scrape_magnum.py"]

SUBSCRIBERS_FILE = "subscribers.json"
LAST_NOTIFIED_FILE = "last_notified.json"
SOUNDS_FOLDER = "sounds"

KL_TZ = ZoneInfo("Asia/Kuala_Lumpur")

DRAW_COLUMNS = (
    ["winning1", "winning2", "winning3"]
    + [f"special{i}" for i in range(1, 11)]
    + [f"consolation{i}" for i in range(1, 11)]
)


def validate_config():
    if not BOT_TOKEN:
        raise RuntimeError("Missing RAND_AI_BOT_TOKEN. Set it before running the bot.")


def is_admin(chat_id):
    return ADMIN_CHAT_ID is not None and int(chat_id) == int(ADMIN_CHAT_ID)


def latest_csv(prefix):
    files = glob.glob(f"{prefix}_pastresult_*.csv")
    return max(files, key=os.path.getmtime) if files else None


def parse_date(date_text):
    try:
        return datetime.strptime(date_text, "%d-%m-%Y")
    except Exception:
        return datetime.min


def load_rows(prefix):
    path = latest_csv(prefix)
    if not path:
        return []

    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    rows.sort(key=lambda r: parse_date(r.get("date", "")))
    return rows


def latest_row(prefix):
    rows = load_rows(prefix)
    return rows[-1] if rows else None


def clean_num(value):
    value = str(value).strip()
    if not value or value == "----":
        return ""
    digits = re.sub(r"\D", "", value)
    return digits.zfill(4)[-4:] if digits else ""


def row_key(row):
    if not row:
        return None

    return (
        f"{row.get('date', '')}|"
        f"{row.get('drawno', '')}|"
        f"{row.get('winning1', '')}|"
        f"{row.get('winning2', '')}|"
        f"{row.get('winning3', '')}"
    )


def load_json_file(path, default):
    if not os.path.exists(path):
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_subscribers():
    return set(load_json_file(SUBSCRIBERS_FILE, []))


def save_subscribers(subscribers):
    save_json_file(SUBSCRIBERS_FILE, sorted(list(subscribers)))


def load_last_notified():
    return load_json_file(LAST_NOTIFIED_FILE, {})


def save_last_notified(data):
    save_json_file(LAST_NOTIFIED_FILE, data)


def run_scrapers():
    for script in SCRAPER_FILES:
        if not os.path.exists(script):
            print(f"[ERROR] Cannot find {script}")
            continue

        print(f"[SCRAPER] Running {script}")

        result = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True
        )

        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print("[SCRAPER ERROR]")
            print(result.stderr)


def ensure_git_remote():
    try:
        remote_check = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True
        )

        current_url = remote_check.stdout.strip()

        if remote_check.returncode != 0:
            subprocess.run(["git", "remote", "add", "origin", GITHUB_REPO_URL], check=True)
            return

        if current_url != GITHUB_REPO_URL:
            subprocess.run(["git", "remote", "set-url", "origin", GITHUB_REPO_URL], check=True)

    except Exception as e:
        print(f"[GIT REMOTE ERROR] {e}")


def git_backup():
    try:
        ensure_git_remote()

        SAFE_GIT_FILES = [
            "bot.py",
            "scrape_toto.py",
            "scrape_magnum.py",
            "README.md",
            ".gitignore",
        ]

        SAFE_PATTERNS = [
            "toto_pastresult_*.csv",
            "magnum_pastresult_*.csv",
        ]

        for file in SAFE_GIT_FILES:
            if os.path.exists(file):
                subprocess.run(["git", "add", file], check=True)

        for pattern in SAFE_PATTERNS:
            for file in glob.glob(pattern):
                subprocess.run(["git", "add", file], check=True)

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True
        )

        if not status.stdout.strip():
            return "GitHub backup skipped. Nothing changed lah."

        commit_msg = f"Auto update 4D dataset {datetime.now(KL_TZ).strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        subprocess.run(["git", "push", "-u", "origin", "main"], check=True)

        return "GitHub backup done already. Dataset safe lah."
    except Exception as e:
        return f"GitHub backup failed: {e}"


def format_result(name, row):
    if not row:
        return (
            f"🏆 {name}\n"
            f"Eh no dataset yet lah.\n"
            f"Run /update first."
        )

    return (
        f"🏆 {name}\n"
        f"Date: {row.get('date', '')}\n"
        f"Draw No: {row.get('drawno', '')}\n"
        f"1st Prize: {row.get('winning1', '')}\n"
        f"2nd Prize: {row.get('winning2', '')}\n"
        f"3rd Prize: {row.get('winning3', '')}"
    )


def latest_message():
    return (
        "🎯 Latest 4D Results\n\n"
        + format_result("Sports Toto", latest_row("toto"))
        + "\n\n"
        + format_result("Magnum", latest_row("magnum"))
    )


async def send_csv_files_to_chat(bot, chat_id):
    for prefix in ["toto", "magnum"]:
        file = latest_csv(prefix)

        if file:
            with open(file, "rb") as f:
                await bot.send_document(
                    chat_id=chat_id,
                    document=f,
                    caption=f"📄 {file}"
                )


async def send_voice_meme(bot, chat_id):

    if not os.path.isdir(SOUNDS_FOLDER):
        return

    files = glob.glob(os.path.join(SOUNDS_FOLDER, "*.*"))
    files = [
        f for f in files
        if f.lower().endswith((".ogg", ".mp3", ".m4a", ".wav"))
    ]

    if not files:
        return

    chosen = random.choice(files)

    with open(chosen, "rb") as f:
        if chosen.lower().endswith(".ogg"):
            await bot.send_voice(chat_id=chat_id, voice=f)
        else:
            await bot.send_audio(chat_id=chat_id, audio=f)


def all_numbers_from_rows(rows):
    nums = []

    for row in rows:
        for col in DRAW_COLUMNS:
            num = clean_num(row.get(col, ""))
            if num:
                nums.append(num)

    return nums


def hot_cold_message(mode="hot", limit_rows=50):
    all_rows = load_rows("toto") + load_rows("magnum")

    if not all_rows:
        return "No dataset yet lah. Run /update first."

    all_rows.sort(key=lambda r: parse_date(r.get("date", "")))
    selected_rows = all_rows[-limit_rows:]

    nums = all_numbers_from_rows(selected_rows)

    if not nums:
        return "No numbers found. Dataset looks empty."

    counter = Counter(nums)

    if mode == "hot":
        selected = counter.most_common(10)
        title = f"🔥 Hot Numbers - Last {limit_rows} rows"
    else:
        selected = sorted(counter.items(), key=lambda x: (x[1], x[0]))[:10]
        title = f"🥶 Cold Numbers - Last {limit_rows} rows"

    lines = [title, ""]

    for num, count in selected:
        lines.append(f"{num} → {count} time(s)")

    return "\n".join(lines)


def search_number_message(number):
    number = clean_num(number)

    if not number:
        return "Give me a proper 4-digit number lah. Example: /search 1234"

    results = []

    for prefix, name in [("toto", "Sports Toto"), ("magnum", "Magnum")]:
        for row in load_rows(prefix):
            found_cols = []

            for col in DRAW_COLUMNS:
                if clean_num(row.get(col, "")) == number:
                    found_cols.append(col)

            if found_cols:
                results.append(
                    f"{name} | {row.get('date', '')} | "
                    f"Draw {row.get('drawno', '')} | {', '.join(found_cols)}"
                )

    if not results:
        return f"Walao, {number} never appear in your dataset yet."

    msg = [f"🔍 Search result for {number}", ""]

    for line in results[-30:]:
        msg.append(line)

    if len(results) > 30:
        msg.append(f"\nShowing latest 30 only. Total found: {len(results)}")

    return "\n".join(msg)


def stats_message():
    toto_rows = load_rows("toto")
    magnum_rows = load_rows("magnum")

    toto_latest = toto_rows[-1] if toto_rows else None
    magnum_latest = magnum_rows[-1] if magnum_rows else None

    return (
        "📊 Daily Statistics\n\n"
        f"Sports Toto rows: {len(toto_rows)}\n"
        f"Latest Toto: {toto_latest.get('date', 'N/A') if toto_latest else 'N/A'}\n\n"
        f"Magnum rows: {len(magnum_rows)}\n"
        f"Latest Magnum: {magnum_latest.get('date', 'N/A') if magnum_latest else 'N/A'}\n\n"
        f"CSV Toto: {latest_csv('toto') or 'No file'}\n"
        f"CSV Magnum: {latest_csv('magnum') or 'No file'}"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    await update.message.reply_text(
        f"Oi, {BOT_NAME} connected already lah 😴\n\n"
        f"Use /subscribe if you want auto result updates.\n\n"
        f"Commands:\n"
        f"/subscribe\n"
        f"/unsubscribe\n"
        f"/update\n"
        f"/result\n"
        f"/search 1234\n"
        f"/hot\n"
        f"/cold\n"
        f"/stats\n"
        f"/help"
    )

    if is_admin(chat_id):
        await update.message.reply_text(
            f"👀 Admin detected.\n"
            f"Walao boss, your admin mode is working already."
        )


async def admincheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if is_admin(chat_id):
        await update.message.reply_text("Walao admin detected 😎")
    else:
        await update.message.reply_text("You not admin lah 😴")


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    subscribers = load_subscribers()
    subscribers.add(chat_id)
    save_subscribers(subscribers)

    await update.message.reply_text(
        "Subscribed already lah. Next result update I will spam you nicely."
    )


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    subscribers = load_subscribers()
    subscribers.discard(chat_id)
    save_subscribers(subscribers)

    await update.message.reply_text(
        "Unsubscribed already. Later don't say I never tell you result ah."
    )


async def update_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Oi, I'm checking the latest Toto and Magnum results now 😴"
    )

    run_scrapers()

    await update.message.reply_text(
        "Oi, here is your result.\n"
        "So lazy until need me to check the result for you..\n\n"
        + latest_message()
    )

    await send_csv_files_to_chat(context.bot, update.effective_chat.id)
    await send_voice_meme(context.bot, update.effective_chat.id)


async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Result already here lah. See properly 😴\n\n"
        + latest_message()
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use like this lah: /search 1234")
        return

    await update.message.reply_text(search_number_message(context.args[0]))


async def hot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    limit = int(context.args[0]) if context.args and context.args[0].isdigit() else 50
    await update.message.reply_text(hot_cold_message("hot", limit))


async def cold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    limit = int(context.args[0]) if context.args and context.args[0].isdigit() else 50
    await update.message.reply_text(hot_cold_message("cold", limit))


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Oi data report coming already, boss 😴\n\n"
        + stats_message()
    )


async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text("Backup command admin only lah. Don't simply press 😴")
        return

    await update.message.reply_text("Backing up to GitHub now. Don't kacau.")
    msg = git_backup()
    await update.message.reply_text(msg)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"{BOT_NAME} commands:\n\n"
        f"/subscribe - receive auto result updates\n"
        f"/unsubscribe - stop auto result updates\n"
        f"/update - scrape and send latest result\n"
        f"/result - show latest saved result\n"
        f"/search 1234 - search old results\n"
        f"/hot - hot numbers\n"
        f"/cold - cold numbers\n"
        f"/stats - dataset statistics\n"
        f"/help - show commands"
    )

    if is_admin(update.effective_chat.id):
        msg += "\n/admincheck - check admin mode\n/backup - push CSV/code to GitHub"

    await update.message.reply_text(msg)


async def check_and_notify(context: ContextTypes.DEFAULT_TYPE, force_no_result_msg=False):
    run_scrapers()

    after_toto = latest_row("toto")
    after_magnum = latest_row("magnum")

    last_data = load_last_notified()

    current = {
        "toto": row_key(after_toto),
        "magnum": row_key(after_magnum),
    }

    has_new = (
        current["toto"] and current["toto"] != last_data.get("toto")
    ) or (
        current["magnum"] and current["magnum"] != last_data.get("magnum")
    )

    subscribers = load_subscribers()

    if ADMIN_CHAT_ID:
        subscribers.add(ADMIN_CHAT_ID)

    if not subscribers:
        print("[INFO] No subscribers yet.")
        return

    if not has_new:
        if force_no_result_msg:
            for chat_id in subscribers:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "Walao eh, no new 4D result yet lah 😴\n"
                        "You refresh so fast for what..."
                    )
                )
        return

    last_data.update(current)
    save_last_notified(last_data)

    text = (
        "Oi, new result keluar already.\n"
        "Need me spoonfeed you everything only happy ah 😴\n\n"
        + latest_message()
    )

    for chat_id in subscribers:
        await context.bot.send_message(chat_id=chat_id, text=text)
        await send_csv_files_to_chat(context.bot, chat_id)
        await send_voice_meme(context.bot, chat_id)

    git_backup()


async def scheduled_9pm(context: ContextTypes.DEFAULT_TYPE):
    await check_and_notify(context, force_no_result_msg=True)


async def instant_polling(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(KL_TZ)

    if 19 <= now.hour <= 23:
        await check_and_notify(context, force_no_result_msg=False)


def main():
    validate_config()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admincheck", admincheck))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CommandHandler("update", update_now))
    app.add_handler(CommandHandler("result", result))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("hot", hot))
    app.add_handler(CommandHandler("cold", cold))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("backup", backup))
    app.add_handler(CommandHandler("help", help_cmd))

    app.job_queue.run_daily(
        scheduled_9pm,
        time=time(hour=21, minute=0, tzinfo=KL_TZ),
        name="daily_9pm_check"
    )

    app.job_queue.run_repeating(
        instant_polling,
        interval=300,
        first=30,
        name="instant_polling_7pm_to_11pm"
    )

    print("===================================")
    print(f"{BOT_NAME} running...")
    print("Commands: /start, /subscribe, /update, /help")
    print("Daily check: 9PM Malaysia Time")
    print("Instant polling: every 5 mins, 7PM-11PM")
    print(f"GitHub backup repo: {GITHUB_REPO_URL}")
    print("===================================")

    app.run_polling()


if __name__ == "__main__":
    main()