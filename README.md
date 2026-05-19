# RandAI Scraper Bot & 4DMoon Scraper

This repository contains **RandAI** (`@RandAI_bot`), a Telegram bot and web scraping suite that extracts historical and current 4D lottery results for **Magnum 4D** and **SportsToto 4D** from [4dmoon.com](https://www.4dmoon.com). It saves them into ordered CSV files, updates local datasets automatically, and provides real-time notifications and statistical analysis through Telegram.

It is designed to be resilient, capable of resuming interrupted tasks, parsing raw string data (instead of complex DOM trees), and automatically repairing the output files if manual tampering causes sorting issues.

## Disclaimer

This project is for educational and data analysis purposes only. Please respect the terms of service of the scraped website and do not overload their servers. The scraper scripts include appropriate delays between requests.

## Features

### Scraping & Data Management
- **Automated Extraction:** Scrapes draw dates, draw numbers, top 3 prizes, special numbers, and consolation numbers.
- **Smart Resuming:** Remembers the last successful page to resume from where it left off, preventing duplicate downloads.
- **Data Repair (Auto-Sort):** If the output CSV gets out of order (e.g., due to manual edits or unexpected interruptions), the scripts can detect and fix it. (Run with `--repair` flag to re-sort the entire CSV chronologically).
- **Raw HTML Parsing:** Instead of relying heavily on complex BeautifulSoup tree traversal, it uses robust Regex on raw string segments.

### Telegram Bot
- **Telegram Notifications:** Subscribed users get automatic updates when new results are released.
- **Smart Polling:** Checks for new results every 5 minutes between 7 PM and 11 PM (Malaysia Time).
- **Number Analysis:** Search historical datasets for past appearances of a specific number, and track hot/cold number trends.
- **Voice Memes:** Sends random voice/audio memes along with results to subscribed users.
- **Automated GitHub Backups:** Commits and pushes new CSV datasets directly to the repository.

## Project Structure

- `bot.py` - The main Telegram bot script that orchestrates scraping, messaging, and commands.
- `scrape_magnum.py` - Scraper and repair tool for Magnum 4D results.
- `scrape_toto.py` - Scraper and repair tool for SportsToto 4D results.
- `sounds/` - Directory for placing `.mp3`, `.ogg`, `.wav`, or `.m4a` files for random voice meme replies.
- `subscribers.json` / `last_notified.json` - Auto-generated data files for tracking Telegram bot subscribers and latest result states.

## Prerequisites

- **Python 3.9+** (Requires `zoneinfo`)
- Packages: `requests`, `beautifulsoup4`, `python-telegram-bot`, `tzdata` (Windows)
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather).
- Git installed and configured (for auto-backup feature).

## Setup & Installation

### 1. Install Dependencies
Install the required Python packages:
```bash
pip install requests beautifulsoup4 python-telegram-bot tzdata
```
*(Note: `tzdata` is required on Windows for timezone support).*

### 2. Configure Environment Variables
The bot requires two environment variables for security. You must set these before running the bot:

- `RAND_AI_BOT_TOKEN`: Your Telegram Bot API token.
- `RAND_AI_ADMIN_CHAT_ID`: (Optional but recommended) Your Telegram Chat ID for admin privileges.

**On Windows (Command Prompt):**
```cmd
set RAND_AI_BOT_TOKEN=your_bot_token_here
set RAND_AI_ADMIN_CHAT_ID=your_chat_id_here
```

**On Windows (PowerShell):**
```powershell
$env:RAND_AI_BOT_TOKEN="your_bot_token_here"
$env:RAND_AI_ADMIN_CHAT_ID="your_chat_id_here"
```

**On Linux/Mac:**
```bash
export RAND_AI_BOT_TOKEN="your_bot_token_here"
export RAND_AI_ADMIN_CHAT_ID="your_chat_id_here"
```

*Tip: If you don't know your Chat ID, you can start the bot without it, send `/start` to the bot, and it will reply with your Chat ID.*

### 3. Verify Configuration
To ensure your environment variables are configured properly before running the bot, you can check their values:

**On Windows (Command Prompt):**
```cmd
echo %RAND_AI_BOT_TOKEN%
echo %RAND_AI_ADMIN_CHAT_ID%
```

**On Windows (PowerShell):**
```powershell
echo $env:RAND_AI_BOT_TOKEN
echo $env:RAND_AI_ADMIN_CHAT_ID
```

**On Linux/Mac:**
```bash
echo $RAND_AI_BOT_TOKEN
echo $RAND_AI_ADMIN_CHAT_ID
```

If the commands return your tokens/IDs, you are ready to go!

### 4. Add Voice Memes (Optional)
If you want the bot to send voice memes with result updates, place any `.mp3`, `.ogg`, or `.wav` files inside the `sounds/` folder.

## Usage

### Running the Telegram Bot
Start the Telegram bot to handle polling, scraping, and commands automatically:
```bash
python bot.py
```
The bot will run continuously, checking for results and listening to commands. 

### Manual Scraping
If you only want to update the CSV datasets without running the bot, you can run the scrapers manually:
```bash
python scrape_magnum.py
python scrape_toto.py
```
*Note: If the script is interrupted, run it again. It will read its last processed state and resume from the correct page without duplicating data.*

### Data Repair Mode
If you suspect the `magnum_history.csv` or `toto_history.csv` is out of chronological order, or if you manually merged files, run the repair flag:
```bash
python scrape_magnum.py --repair
python scrape_toto.py --repair
```
This will read the existing CSV, sort all rows by `Draw Date` (ascending), remove duplicates, and overwrite the file securely.

## Telegram Commands

Once the bot is running, interact with it on Telegram using these commands:

- `/start` - Check if the bot is alive and get your Chat ID.
- `/subscribe` - Opt-in to receive automatic messages when new 4D results are published.
- `/unsubscribe` - Stop receiving automatic results.
- `/update` - Force the scrapers to run immediately and send the latest results.
- `/result` - Show the latest results saved in the local dataset.
- `/search <number>` - Check past appearances of a 4-digit number (e.g., `/search 1234`).
- `/hot [limit]` - Show the most frequently drawn numbers in the last X draws (default 50).
- `/cold [limit]` - Show the least frequently drawn numbers in the last X draws.
- `/stats` - View dataset statistics.
- `/backup` - Commit and push the local dataset to GitHub.

## Auto Backup Feature
The `/backup` command (and auto-notification backup) uses your local Git configuration. Ensure your Git remote origin points to your repository (`https://github.com/lck920/randai-scraper-bot`) and you have the necessary push permissions authenticated on your machine.
