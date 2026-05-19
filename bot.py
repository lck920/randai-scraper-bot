"""
========================================================
RandAI Telegram Bot (@RandAI_bot)
Author: lck920
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
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


BOT_NAME = "@RandAI_bot"
GITHUB_REPO_URL = "https://github.com/lck920/randai-scraper-bot"

BOT_TOKEN = os.getenv("RAND_AI_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("RAND_AI_ADMIN_CHAT_ID")
ADMIN_CHAT_ID = int(ADMIN_CHAT_ID) if ADMIN_CHAT_ID else None

DATA_DIR = "data"
SOUNDS_FOLDER = "sounds"

SCRAPER_FILES = [
    "scrape_toto.py",
    "scrape_magnum.py",
]

SUBSCRIBERS_FILE = "subscribers.json"
LAST_NOTIFIED_FILE = "last_notified.json"

KL_TZ = ZoneInfo("Asia/Kuala_Lumpur")

DRAW_COLUMNS = (
    ["winning1", "winning2", "winning3"]
    + [f"special{i}" for i in range(1, 11)]
    + [f"consolation{i}" for i in range(1, 11)]
)


def validate_config():
    if not BOT_TOKEN:
        raise RuntimeError("Missing RAND_AI_BOT_TOKEN environment variable.")


def is_admin(chat_id):
    return ADMIN_CHAT_ID is not None and int(chat_id) == int(ADMIN_CHAT_ID)


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


def latest_csv(prefix):
    files = glob.glob(os.path.join(DATA_DIR, f"{prefix}_pastresult_*.csv"))
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


def msg_start_menu(bot_name):
    toto = latest_row("toto")
    magnum = latest_row("magnum")

    if toto or magnum:
        latest_dates = []

        if toto:
            latest_dates.append(f"🎰 Toto: {toto.get('date', 'N/A')}")

        if magnum:
            latest_dates.append(f"🎰 Magnum: {magnum.get('date', 'N/A')}")

        latest_section = "📌 Latest Updated Results\n" + "\n".join(latest_dates)
    else:
        latest_section = (
            "⚠️ No dataset found yet lah 😴\n"
            "Use /update first so RandAI can build the data/ folder."
        )

    return (
        f"Oi, {bot_name} online already lah 😴\n\n"
        f"I’m RandAI — your lazy-but-useful 4D result bot.\n"
        f"I scrape Toto & Magnum from 4dmoon, update datasets, analyse numbers, "
        f"and spoonfeed results to lazy people.\n\n"
        f"{latest_section}\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"📌 MAIN COMMANDS\n\n"
        f"🔔 /subscribe\n"
        f"Get auto result updates.\n\n"
        f"🔕 /unsubscribe\n"
        f"Stop auto notifications.\n\n"
        f"🔄 /update\n"
        f"Force RandAI to scrape latest results now.\n\n"
        f"📦 /result\n"
        f"Show latest saved result from local data/.\n\n"
        f"🔍 /search 1234\n"
        f"Search old result history.\n\n"
        f"🔥 /hot\n"
        f"Show hot numbers.\n\n"
        f"🥶 /cold\n"
        f"Show cold numbers.\n\n"
        f"📊 /stats\n"
        f"Show dataset statistics.\n\n"
        f"🆘 /help\n"
        f"Show full command explanation.\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"🤖 RandAI Status: ONLINE\n"
    )


MSG_ADMIN_OK = "👀 Admin detected. Boss mode unlocked already lah 😎"
MSG_NOT_ADMIN = "You not admin lah. Don’t act like owner 😴"
MSG_SUBSCRIBED = "Subscribed already lah 🔔\nNext result keluar I notify you automatically."
MSG_UNSUBSCRIBED = "Unsubscribed already 🔕\nLater don’t ask why RandAI never tell you result ah."
MSG_CHECKING = "Oi, checking latest Toto & Magnum results now 😴\nDon’t rush me lah, scraping also need dignity one."
MSG_RESULT_HEADER = "Oi, result ready already 😴\nSee properly ah.\n\n"
MSG_NO_NEW_RESULT = "Walao eh, no new result yet lah 😴\nYou refresh so fast for what..."
MSG_NEW_RESULT = "🚨 Oi, new result keluar already.\nRandAI spoonfeed you nicely again 😴\n\n"
MSG_BACKUP_START = "Backing up to GitHub now.\nSerious work in progress 😎"
MSG_BACKUP_NOT_ADMIN = "Backup command admin only lah 😴"
MSG_NO_DATASET = (
    "Eh no local dataset found yet lah 😴\n"
    "I scraping from scratch now.\n"
    "This one may take longer, go drink water first."
)
MSG_FOUND_DATASET = "Found existing local dataset already.\nChecking latest updates now..."


def format_column_name(col):
    if col == "winning1":
        return "1st Prize"
    if col == "winning2":
        return "2nd Prize"
    if col == "winning3":
        return "3rd Prize"
    if col.startswith("special"):
        return f"Special #{col.replace('special', '')}"
    if col.startswith("consolation"):
        return f"Consolation #{col.replace('consolation', '')}"
    return col


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

async def scheduled_9pm(context: ContextTypes.DEFAULT_TYPE):

    print("[AUTO UPDATE] 9PM Malaysia update started")

    await check_and_notify(
        context,
        force_no_result_msg=False
    )

async def send_sound(bot, chat_id):
    if not os.path.isdir(SOUNDS_FOLDER):
        return

    files = glob.glob(os.path.join(SOUNDS_FOLDER, "*.*"))
    files = [f for f in files if f.lower().endswith((".ogg", ".mp3", ".wav", ".m4a"))]

    if not files:
        return

    chosen = random.choice(files)

    with open(chosen, "rb") as f:
        if chosen.lower().endswith(".ogg"):
            await bot.send_voice(chat_id=chat_id, voice=f)
        else:
            await bot.send_audio(chat_id=chat_id, audio=f)


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


async def run_scrapers_with_progress(bot, chat_id):
    for script in SCRAPER_FILES:
        prefix = "toto" if "toto" in script.lower() else "magnum"

        if not latest_csv(prefix):
            await bot.send_message(chat_id=chat_id, text=f"{prefix.upper()}\n\n{MSG_NO_DATASET}")
        else:
            await bot.send_message(chat_id=chat_id, text=f"{prefix.upper()}\n\n{MSG_FOUND_DATASET}")

        await bot.send_message(chat_id=chat_id, text=f"🚀 Running {script} now...")

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
                await bot.send_message(chat_id=chat_id, text=f"✅ {script} done already lah.")
            else:
                await bot.send_message(chat_id=chat_id, text=f"❌ {script} got problem lah. Exit code: {process.returncode}")

        except Exception as e:
            await bot.send_message(chat_id=chat_id, text=f"❌ RandAI failed to run {script}: {e}")


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

        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)

        if not status.stdout.strip():
            return "GitHub backup skipped. Nothing changed lah."

        commit_msg = f"Auto update 4D dataset {datetime.now(KL_TZ).strftime('%Y-%m-%d %H:%M')}"

        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        subprocess.run(["git", "push", "-u", "origin", "main"], check=True)

        return "GitHub backup done already 😎"

    except Exception as e:
        return f"GitHub backup failed: {e}"


def all_numbers_from_rows(rows):
    nums = []

    for row in rows:
        for col in DRAW_COLUMNS:
            num = clean_num(row.get(col, ""))

            if num:
                nums.append(num)

    return nums


def hot_cold_message(mode="hot", limit_rows=50):
    """
    Generates a message containing the most (hot) or least (cold) 
    frequently drawn numbers in recent draws.
    """
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
        title = "🔥 RandAI Hot Number Board"
        subtitle = "Most frequent numbers recently"
    else:
        selected = sorted(counter.items(), key=lambda x: (x[1], x[0]))[:10]
        title = "🥶 RandAI Cold Number Board"
        subtitle = "Least frequent numbers recently"

    lines = [
        title,
        subtitle,
        "",
        f"📊 Based on last {limit_rows} rows",
        "━━━━━━━━━━━━━━",
    ]

    medals = ["🥇", "🥈", "🥉"]

    for index, (num, count) in enumerate(selected, start=1):
        rank = medals[index - 1] if index <= 3 else f"{index}."
        lines.append(f"{rank} {num}  —  {count} time(s)")

    lines.extend([
        "━━━━━━━━━━━━━━",
        "RandAI analysis only ah, don’t all-in like hero 😴"
    ])

    return "\n".join(lines)


def search_number_message(number):
    """
    Searches the datasets for past appearances of a specific 4-digit number.
    Returns a formatted message containing all the found results.
    """
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
                    found_cols.append(format_column_name(col))

            if found_cols:
                results.append(
                    f"🎯 {name}\n"
                    f"📅 {row.get('date', '')}\n"
                    f"🎲 Draw {row.get('drawno', '')}\n"
                    f"📌 Position: {', '.join(found_cols)}\n"
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

    total_rows = len(toto_rows) + len(magnum_rows)

    lines = [
        "📊 RandAI Dataset Intelligence Report 😴",
        "",
        "━━━━━━━━━━━━━━",
        "🎰 SPORTS TOTO",
        f"📦 Total Rows: {len(toto_rows)}",
        f"📅 Latest Result: {toto_latest.get('date', 'N/A') if toto_latest else 'N/A'}",
        "💾 Dataset File:",
        f"`{os.path.basename(latest_csv('toto')) if latest_csv('toto') else 'No CSV'}`",
        "",
        "━━━━━━━━━━━━━━",
        "🎰 MAGNUM",
        f"📦 Total Rows: {len(magnum_rows)}",
        f"📅 Latest Result: {magnum_latest.get('date', 'N/A') if magnum_latest else 'N/A'}",
        "💾 Dataset File:",
        f"`{os.path.basename(latest_csv('magnum')) if latest_csv('magnum') else 'No CSV'}`",
        "",
        "━━━━━━━━━━━━━━",
        "🧠 OVERALL SYSTEM",
        f"📊 Combined Rows: {total_rows}",
        f"📁 Data Folder: `{DATA_DIR}/`",
        "🤖 Bot Status: ONLINE",
        "",
        "RandAI still working harder than some humans 😴"
    ]

    return "\n".join(lines)


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
        "Force RandAI to scrape latest results now.\n\n"
        "📦 /result\n"
        "Show latest saved Toto & Magnum result from data/.\n\n"
        "🔍 /search 1234\n"
        "Search whether a 4-digit number appeared before.\n\n"
        "🔥 /hot\n"
        "Show most frequent numbers recently.\n\n"
        "🥶 /cold\n"
        "Show least frequent numbers.\n\n"
        "📊 /stats\n"
        "Show dataset statistics.\n\n"
        "🆘 /help\n"
        "You already using this now 😭\n\n"
        "Use properly ah. RandAI not your unpaid intern 😴"
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

    status_msg = await update.message.reply_text(
        "🤖 RandAI checking latest Toto & Magnum results...\n\n"
        "Please wait ah 😴"
    )

    run_scrapers_silent()

    toto_rows = load_rows("toto")
    magnum_rows = load_rows("magnum")

    toto_latest = latest_row("toto")
    magnum_latest = latest_row("magnum")

    summary = (
        "✅ RandAI update completed\n\n"

        "🎰 Sports Toto\n"
        f"📅 Latest Result: {toto_latest.get('date', 'N/A') if toto_latest else 'N/A'}\n"
        f"📦 Total Rows: {len(toto_rows)}\n\n"

        "🎰 Magnum\n"
        f"📅 Latest Result: {magnum_latest.get('date', 'N/A') if magnum_latest else 'N/A'}\n"
        f"📦 Total Rows: {len(magnum_rows)}\n\n"

        "━━━━━━━━━━━━━━\n"
        "🎯 Sending latest results now..."
    )

    await status_msg.edit_text(summary)

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
        await update.message.reply_text("Use properly lah 😴\nExample: /search 1234")
        return

    await update.message.reply_text(search_number_message(context.args[0]))


async def hot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    limit = int(context.args[0]) if context.args and context.args[0].isdigit() else 50
    await update.message.reply_text(hot_cold_message("hot", limit))


async def cold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    limit = int(context.args[0]) if context.args and context.args[0].isdigit() else 50
    await update.message.reply_text(hot_cold_message("cold", limit))


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(stats_message(), parse_mode="Markdown")


async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text(MSG_BACKUP_NOT_ADMIN)
        return

    await update.message.reply_text(MSG_BACKUP_START)

    msg = git_backup()

    await update.message.reply_text(msg)


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    messages = [
        "Idk what u say la 😭\nUse command la cibai.\n\nType /start to see main menu.",
        "Type weird weird thing for what 😴\nUse command la cibai.\n\nIf blur blur, use /start.",
        "RandAI not mind reader leh 😭\nUse proper command la cibai.\n\nTry /start for menu.",
        "Aiyo...\nI only understand commands 😴\n\nUse /start if your brain loading.",
        "Walao eh.\nYou think I ChatGPT is it 😭\nUse command la cibai.\n\nType /start for available commands.",
    ]

    await update.message.reply_text(random.choice(messages))


async def check_and_notify(context: ContextTypes.DEFAULT_TYPE, target_users=None, force_no_result_msg=False):
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

    if target_users is None:
        subscribers = load_subscribers()
        if ADMIN_CHAT_ID:
            subscribers.add(ADMIN_CHAT_ID)
    else:
        subscribers = set(target_users)

    if not subscribers:
        print("[INFO] No subscribers yet.")
        return

    if not has_new:
        if force_no_result_msg:
            for chat_id in subscribers:
                await context.bot.send_message(chat_id=chat_id, text=MSG_NO_NEW_RESULT)
        return

    last_data.update(current)
    save_last_notified(last_data)

    text = MSG_NEW_RESULT + latest_message()

    for chat_id in subscribers:
        await context.bot.send_message(chat_id=chat_id, text=text)
        await send_csv_files_to_chat(context.bot, chat_id)
        await send_sound(context.bot, chat_id)

async def user_time_notifier(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(KL_TZ).strftime("%H:%M")

    subscribers = load_subscribers()

    if ADMIN_CHAT_ID:
        subscribers.add(ADMIN_CHAT_ID)

    if not subscribers:
        return

    target_users = [
        chat_id for chat_id in subscribers
        if get_user_notify_time(chat_id) == now
    ]

    if not target_users:
        return

    await check_and_notify(
        context,
        target_users=target_users,
        force_no_result_msg=True
    )


async def instant_polling(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(KL_TZ)

    if 19 <= now.hour <= 23:
        await check_and_notify(context, force_no_result_msg=False)


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

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    app.job_queue.run_daily(
        scheduled_9pm,
        time=time(hour=21, minute=0, tzinfo=KL_TZ),
        name="daily_9pm_update"
    )

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🤖 RandAI Telegram Bot Online")
    print(f"📌 Bot Name: {BOT_NAME}")
    print("📡 Status: RUNNING")
    print("⏰ Auto Update: Daily 9:00 PM (Malaysia Time)")
    print("📂 Dataset Folder: data/")
    print("🔔 Subscribers System: ENABLED")
    print("💾 GitHub Auto Backup: DISABLED")
    print("")
    print("📌 Available Commands")
    print("/start")
    print("/subscribe")
    print("/unsubscribe")
    print("/update")
    print("/dataset")
    print("/search 1234")
    print("/hot")
    print("/cold")
    print("/stats")
    print("/help")
    print("")
    print(f"🌐 GitHub Repo:")
    print(GITHUB_REPO_URL)
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    app.run_polling()


if __name__ == "__main__":
    main()