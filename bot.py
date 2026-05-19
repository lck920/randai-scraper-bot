"""
========================================================
RandAI Telegram Bot (@RandAI_bot)
Author: Jackson / lck920
GitHub: https://github.com/lck920/randai-scraper-bot
========================================================

Required environment variables:
RAND_AI_BOT_TOKEN
RAND_AI_ADMIN_CHAT_ID

Main features:
- Telegram bot for Toto & Magnum 4D results
- Saves/reads CSV files from data/
- Multi-user subscription
- Auto 9PM check
- Optional 7PM–11PM polling
- Hot/cold number analysis
- Search old results
- GitHub backup without pushing confidential files
- Random sound replies from sounds/
========================================================
"""

import os
import re
import csv
import sys
import json
import glob
import random
import asyncio
import subprocess
from collections import Counter
from datetime import datetime, time
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes


# ========================================================
# CONFIG
# ========================================================

BOT_NAME = "@RandAI_bot"
GITHUB_REPO_URL = "https://github.com/lck920/randai-scraper-bot"

BOT_TOKEN = os.getenv("RAND_AI_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("RAND_AI_ADMIN_CHAT_ID")
ADMIN_CHAT_ID = int(ADMIN_CHAT_ID) if ADMIN_CHAT_ID else None

DATA_DIR = "data"
SOUNDS_FOLDER = "sounds"

SCRAPER_FILES = [
    os.path.join("scrapers", "scrape_toto.py"),
    os.path.join("scrapers", "scrape_magnum.py"),
]

SUBSCRIBERS_FILE = "subscribers.json"
LAST_NOTIFIED_FILE = "last_notified.json"

KL_TZ = ZoneInfo("Asia/Kuala_Lumpur")

DRAW_COLUMNS = (
    ["winning1", "winning2", "winning3"]
    + [f"special{i}" for i in range(1, 11)]
    + [f"consolation{i}" for i in range(1, 11)]
)


# ========================================================
# RANDAI STYLE MESSAGES
# ========================================================

def msg_start_menu(bot_name):
    return (
        f"Oi, {bot_name} online already lah 😴\n\n"
        f"I’m RandAI — your lazy-but-useful 4D result bot.\n"
        f"I check Toto & Magnum from 4dmoon, update your CSV, analyse numbers, "
        f"and notify you when new result keluar.\n\n"
        f"📌 What I can do:\n"
        f"• Auto-check Toto & Magnum results\n"
        f"• Update local CSV datasets inside data/\n"
        f"• Notify subscribers when new results appear\n"
        f"• Search old numbers\n"
        f"• Show hot/cold number analysis\n"
        f"• Send CSV files\n"
        f"• Auto backup safe files to GitHub\n\n"
        f"Commands:\n\n"
        f"🔔 /subscribe — get auto result updates\n"
        f"🔕 /unsubscribe — stop auto updates\n"
        f"🔄 /update — manually scrape latest result now\n"
        f"📦 /dataset — show latest saved result from database\n"
        f"🔍 /search 1234 — search old results\n"
        f"🔥 /hot — show hot numbers\n"
        f"🥶 /cold — show cold numbers\n"
        f"📊 /stats — dataset statistics\n"
        f"🆘 /help — show command list\n\n"
        f"Use properly ah, don’t spam me like loan shark bot 😴"
    )


MSG_ADMIN_OK = "👀 Admin detected. Boss mode unlocked already lah 😎"
MSG_NOT_ADMIN = "You not admin lah. Don’t act like owner 😴"

MSG_SUBSCRIBED = (
    "Subscribed already lah 🔔\n"
    "Next result keluar I notify you automatically."
)

MSG_UNSUBSCRIBED = (
    "Unsubscribed already 🔕\n"
    "Later don’t ask why RandAI never tell you result ah."
)

MSG_CHECKING = (
    "Oi, checking latest Toto & Magnum results now 😴\n"
    "Don’t rush me lah, scraping also need dignity one."
)

MSG_RESULT_HEADER = (
    "Oi, result ready already 😴\n"
    "See properly ah.\n\n"
)

MSG_NO_NEW_RESULT = (
    "Walao eh, no new result yet lah 😴\n"
    "You refresh so fast for what..."
)

MSG_NEW_RESULT = (
    "🚨 Oi, new result keluar already.\n"
    "RandAI spoonfeed you nicely again 😴\n\n"
)

MSG_BACKUP_START = (
    "Backing up to GitHub now.\n"
    "Serious work in progress 😎"
)

MSG_BACKUP_NOT_ADMIN = "Backup command admin only lah 😴"

MSG_NO_DATASET = (
    "Eh no local dataset found yet lah 😴\n"
    "I scraping from scratch now.\n"
    "This one may take longer, go drink water first."
)

MSG_FOUND_DATASET = (
    "Found existing local dataset already.\n"
    "Checking latest updates now..."
)


# ========================================================
# VALIDATION / ADMIN
# ========================================================

def validate_config():
    if not BOT_TOKEN:
        raise RuntimeError(
            "Missing RAND_AI_BOT_TOKEN environment variable."
        )


def is_admin(chat_id):
    return ADMIN_CHAT_ID is not None and int(chat_id) == int(ADMIN_CHAT_ID)


# ========================================================
# JSON HELPERS
# ========================================================

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


# ========================================================
# CSV HELPERS
# ========================================================

def latest_csv(prefix):
    files = glob.glob(
        os.path.join(
            DATA_DIR,
            f"{prefix}_pastresult_*.csv"
        )
    )

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


# ========================================================
# RESULT FORMAT
# ========================================================

def format_result(name, row):
    if not row:
        return (
            f"🏆 {name}\n"
            f"No dataset yet lah.\n"
            f"Run /update first and let RandAI build data/ for you."
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


# ========================================================
# SOUNDS
# ========================================================

async def send_sound(bot, chat_id):
    if not os.path.isdir(SOUNDS_FOLDER):
        return

    files = glob.glob(os.path.join(SOUNDS_FOLDER, "*.*"))

    files = [
        f for f in files
        if f.lower().endswith((".ogg", ".mp3", ".wav", ".m4a"))
    ]

    if not files:
        return

    chosen = random.choice(files)

    with open(chosen, "rb") as f:
        if chosen.lower().endswith(".ogg"):
            await bot.send_voice(chat_id=chat_id, voice=f)
        else:
            await bot.send_audio(chat_id=chat_id, audio=f)


# ========================================================
# SEND CSV
# ========================================================

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


# ========================================================
# SCRAPER WITH PROGRESS
# ========================================================

async def run_scrapers_with_progress(bot, chat_id):
    for script in SCRAPER_FILES:
        prefix = "toto" if "toto" in script.lower() else "magnum"

        if not latest_csv(prefix):
            await bot.send_message(
                chat_id=chat_id,
                text=f"{prefix.upper()}\n\n{MSG_NO_DATASET}"
            )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=f"{prefix.upper()}\n\n{MSG_FOUND_DATASET}"
            )

        await bot.send_message(
            chat_id=chat_id,
            text=f"🚀 Running {script} now..."
        )

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-u",
                script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            progress_counter = 0

            while True:
                line = await process.stdout.readline()

                if not line:
                    break

                text = line.decode("utf-8", errors="replace").strip()
                print(text)

                important = (
                    "No local dataset" in text
                    or "Found existing" in text
                    or "Fetching/checking" in text
                    or "Loaded" in text
                    or "OK" in text
                    or "SKIP" in text
                    or "Saved" in text
                    or "ERROR" in text
                )

                if important:
                    progress_counter += 1

                    if progress_counter % 10 == 0 or "Saved" in text or "ERROR" in text:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"📈 Progress Update\n\n{text}"
                        )

            await process.wait()

            if process.returncode == 0:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ {script} done already lah."
                )
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ {script} got problem lah. Exit code: {process.returncode}"
                )

        except Exception as e:
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ RandAI failed to run {script}: {e}"
            )


def run_scrapers_silent():
    for script in SCRAPER_FILES:
        if not os.path.exists(script):
            print(f"[ERROR] Cannot find {script}")
            continue

        print(f"[SCRAPER] Running {script}")

        try:
            result = subprocess.run(
                [sys.executable, script],
                capture_output=True,
                text=True,
                timeout=300,
                encoding="utf-8",
                errors="replace"
            )

            if result.stdout:
                print(result.stdout)

            if result.stderr:
                print("[SCRAPER ERROR]")
                print(result.stderr)

        except subprocess.TimeoutExpired:
            print(f"[TIMEOUT] {script} took too long. Killed already lah.")

        except Exception as e:
            print(f"[ERROR] Failed running {script}: {e}")


# ========================================================
# GITHUB BACKUP
# ========================================================

def ensure_git_remote():
    try:
        remote_check = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True
        )

        current_url = remote_check.stdout.strip()

        if remote_check.returncode != 0:
            subprocess.run(
                ["git", "remote", "add", "origin", GITHUB_REPO_URL],
                check=True
            )
            return

        if current_url != GITHUB_REPO_URL:
            subprocess.run(
                ["git", "remote", "set-url", "origin", GITHUB_REPO_URL],
                check=True
            )

    except Exception as e:
        print(f"[GIT REMOTE ERROR] {e}")


def git_backup():
    try:
        ensure_git_remote()

        safe_files = [
            "bot.py",
            "scrape_toto.py",
            "scrape_magnum.py",
            ".gitignore",
            "README.md",
        ]

        safe_patterns = [
            os.path.join(DATA_DIR, "toto_pastresult_*.csv"),
            os.path.join(DATA_DIR, "magnum_pastresult_*.csv"),
        ]

        for file in safe_files:
            if os.path.exists(file):
                subprocess.run(["git", "add", file], check=True)

        for pattern in safe_patterns:
            for file in glob.glob(pattern):
                subprocess.run(["git", "add", file], check=True)

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True
        )

        if not status.stdout.strip():
            return "GitHub backup skipped. Nothing changed lah."

        commit_msg = (
            f"Auto update 4D dataset "
            f"{datetime.now(KL_TZ).strftime('%Y-%m-%d %H:%M')}"
        )

        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        subprocess.run(["git", "push", "-u", "origin", "main"], check=True)

        return "GitHub backup done already 😎"

    except Exception as e:
        return f"GitHub backup failed: {e}"


# ========================================================
# ANALYSIS
# ========================================================

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
        return "No dataset yet lah 😴 Run /update first."

    all_rows.sort(key=lambda r: parse_date(r.get("date", "")))

    selected_rows = all_rows[-limit_rows:]
    nums = all_numbers_from_rows(selected_rows)

    if not nums:
        return "Dataset got no numbers. Something weird lah."

    counter = Counter(nums)

    if mode == "hot":
        selected = counter.most_common(10)
        title = f"🔥 Hot Numbers\nBased on last {limit_rows} rows\n"
    else:
        selected = sorted(counter.items(), key=lambda x: (x[1], x[0]))[:10]
        title = f"🥶 Cold Numbers\nBased on last {limit_rows} rows\n"

    lines = [title]

    for num, count in selected:
        lines.append(f"{num} -> {count} time(s)")

    return "\n".join(lines)


def search_number_message(number):
    number = clean_num(number)

    if not number:
        return "Use properly lah 😴 Example: /search 1234"

    results = []

    for prefix, name in [
        ("toto", "Sports Toto"),
        ("magnum", "Magnum"),
    ]:
        for row in load_rows(prefix):
            found_cols = []

            for col in DRAW_COLUMNS:
                if clean_num(row.get(col, "")) == number:
                    found_cols.append(col)

            if found_cols:
                results.append(
                    f"{name} | "
                    f"{row.get('date', '')} | "
                    f"Draw {row.get('drawno', '')} | "
                    f"{', '.join(found_cols)}"
                )

    if not results:
        return f"Walao, {number} never appear before leh 😴"

    msg = [f"🔍 Search Result for {number}\n"]

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
        "📊 RandAI Dataset Statistics\n\n"
        f"Sports Toto rows: {len(toto_rows)}\n"
        f"Latest Toto date: {toto_latest.get('date', 'N/A') if toto_latest else 'N/A'}\n"
        f"Latest Toto CSV: {latest_csv('toto') or 'No file'}\n\n"
        f"Magnum rows: {len(magnum_rows)}\n"
        f"Latest Magnum date: {magnum_latest.get('date', 'N/A') if magnum_latest else 'N/A'}\n"
        f"Latest Magnum CSV: {latest_csv('magnum') or 'No file'}"
    )


# ========================================================
# COMMANDS
# ========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(msg_start_menu(BOT_NAME))

    if is_admin(update.effective_chat.id):
        await update.message.reply_text(MSG_ADMIN_OK)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "U stupid is it? 😴\n"
        "Still need type /help somemore...\n\n"
        "Nevermind lah, RandAI explain again.\n\n"
        "📌 COMMAND LIST\n\n"
        "🔔 /subscribe\n"
        "Subscribe to auto Toto & Magnum updates.\n"
        "New result keluar = I notify you automatically.\n\n"
        "🔕 /unsubscribe\n"
        "Stop notifications.\n"
        "Later don’t ask why nobody tell you result ah.\n\n"
        "🔄 /update\n"
        "Force RandAI to scrape latest results now.\n"
        "Good for impatient people 😴\n\n"
        "📦 /dataset\n"
        "Show latest saved Toto & Magnum result from data/.\n"
        "This one read local dataset only.\n\n"
        "🔍 /search 1234\n"
        "Search whether a 4-digit number appeared before.\n"
        "Good for pattern hunters and delulu gamblers.\n\n"
        "🔥 /hot\n"
        "Show most frequent numbers recently.\n"
        "Hot until can fry egg already.\n\n"
        "🥶 /cold\n"
        "Show least frequent numbers.\n"
        "Cold until penguin also shiver.\n\n"
        "📊 /stats\n"
        "Show dataset statistics.\n"
        "Rows, latest CSV, latest dates all inside.\n\n"
        "🆘 /help\n"
        "You already using this now 😭\n\n"
        "Use properly ah.\n"
        "RandAI not your unpaid intern 😴"
    )

    if is_admin(update.effective_chat.id):
        msg += (
            "\n\n👑 ADMIN COMMANDS\n\n"
            "💾 /backup\n"
            "Push latest datasets/code to GitHub.\n\n"
            "🕵️ /admincheck\n"
            "Check whether boss mode working."
        )

    await update.message.reply_text(msg)


async def admincheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_chat.id):
        await update.message.reply_text(MSG_ADMIN_OK)
    else:
        await update.message.reply_text(MSG_NOT_ADMIN)


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    subscribers = load_subscribers()
    subscribers.add(chat_id)
    save_subscribers(subscribers)

    await update.message.reply_text(MSG_SUBSCRIBED)


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    subscribers = load_subscribers()
    subscribers.discard(chat_id)
    save_subscribers(subscribers)

    await update.message.reply_text(MSG_UNSUBSCRIBED)


async def update_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MSG_CHECKING)

    await run_scrapers_with_progress(
        context.bot,
        update.effective_chat.id
    )

    await update.message.reply_text(
        MSG_RESULT_HEADER + latest_message()
    )

    await send_csv_files_to_chat(
        context.bot,
        update.effective_chat.id
    )

    await send_sound(
        context.bot,
        update.effective_chat.id
    )


async def dataset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 RandAI Dataset Loaded 😴\n\n"
        "Here your latest saved Toto & Magnum result lah.\n"
        "Local data/ folder one, not live scrape.\n\n"
        + latest_message()
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Use properly lah 😴\nExample: /search 1234"
        )
        return

    await update.message.reply_text(
        search_number_message(context.args[0])
    )


async def hot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    limit = (
        int(context.args[0])
        if context.args and context.args[0].isdigit()
        else 50
    )

    await update.message.reply_text(
        hot_cold_message("hot", limit)
    )


async def cold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    limit = (
        int(context.args[0])
        if context.args and context.args[0].isdigit()
        else 50
    )

    await update.message.reply_text(
        hot_cold_message("cold", limit)
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Oi data report coming already 😴\n\n"
        + stats_message()
    )


async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text(MSG_BACKUP_NOT_ADMIN)
        return

    await update.message.reply_text(MSG_BACKUP_START)

    msg = git_backup()

    await update.message.reply_text(msg)


# ========================================================
# AUTO NOTIFICATION
# ========================================================

async def check_and_notify(context: ContextTypes.DEFAULT_TYPE, force_no_result_msg=False):
    run_scrapers_silent()

    after_toto = latest_row("toto")
    after_magnum = latest_row("magnum")

    current = {
        "toto": row_key(after_toto),
        "magnum": row_key(after_magnum),
    }

    last_data = load_last_notified()

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
                    text=MSG_NO_NEW_RESULT
                )
        return

    last_data.update(current)
    save_last_notified(last_data)

    text = MSG_NEW_RESULT + latest_message()

    for chat_id in subscribers:
        await context.bot.send_message(chat_id=chat_id, text=text)

        await send_csv_files_to_chat(
            context.bot,
            chat_id
        )

        await send_sound(
            context.bot,
            chat_id
        )

    git_backup()


async def scheduled_9pm(context: ContextTypes.DEFAULT_TYPE):
    await check_and_notify(
        context,
        force_no_result_msg=True
    )


async def instant_polling(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(KL_TZ)

    if 19 <= now.hour <= 23:
        await check_and_notify(
            context,
            force_no_result_msg=False
        )


# ========================================================
# MAIN
# ========================================================

def main():
    validate_config()

    os.makedirs(DATA_DIR, exist_ok=True)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))

    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))

    app.add_handler(CommandHandler("update", update_now))
    app.add_handler(CommandHandler("dataset", dataset))

    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("hot", hot))
    app.add_handler(CommandHandler("cold", cold))
    app.add_handler(CommandHandler("stats", stats))

    app.add_handler(CommandHandler("backup", backup))
    app.add_handler(CommandHandler("admincheck", admincheck))

    app.job_queue.run_daily(
        scheduled_9pm,
        time=time(hour=21, minute=0, tzinfo=KL_TZ),
        name="daily_9pm_check"
    )

    # Comment this block during testing if it keeps scraping too often.
    app.job_queue.run_repeating(
        instant_polling,
        interval=300,
        first=30,
        name="instant_polling_7pm_to_11pm"
    )

    print("===================================")
    print(f"{BOT_NAME} running...")
    print("Commands: /start, /subscribe, /update, /dataset, /help")
    print("Daily check: 9PM Malaysia Time")
    print("Instant polling: every 5 mins, 7PM-11PM")
    print(f"GitHub backup repo: {GITHUB_REPO_URL}")
    print("===================================")

    app.run_polling()


if __name__ == "__main__":
    main()