# RandAI Telegram Bot

[![Bot Status](https://img.shields.io/badge/Status-Online-success.svg)](#)

**RandAI (@RandAI_bot)** is an intelligent, lazy-but-useful Telegram bot that scrapes, auto-sorts, and serves Toto and Magnum 4D lottery results on demand or automatically via subscription. The bot manages datasets locally in CSV format, provides detailed historical number analysis (hot/cold numbers), allows users to search for past numbers, and offers a manual backup mechanism for administrators. It is tailored with a humorous, local Malaysian/Singaporean "Manglish" tone to keep interactions lighthearted.

## 🚀 Features

- **Automated Data Scraping:** Retrieves the latest Toto & Magnum 4D results directly from 4dmoon.
- **Multi-user Subscription System:** Users can subscribe via Telegram to receive automatic, instant result and CSV updates as soon as they drop.
- **Smart Analytics:** Analyze datasets to display the "hottest" (most frequently drawn) and "coldest" (least frequently drawn) numbers.
- **Search History:** Query specific 4-digit numbers to see exactly when and where they appeared in past draws.
- **Scheduled Auto-Updates:** Built-in auto-checking and broadcasting at 9 PM (Malaysia Time) on draw days for hands-free spoonfeeding.
- **Admin Dashboard:** Admins can securely back up the datasets and code to GitHub straight from the Telegram chat without pushing any confidential keys.
- **Fun Integrations:** Sends random audio clips (from the `sounds/` directory) alongside the results to keep it entertaining!

## 📂 Project Structure

```
randai-scraper-bot/
├── .env.example          # Example environment variable file
├── bot.py                # Main Telegram bot logic and message handling
├── scrape_magnum.py      # Scraper script dedicated to Magnum 4D
├── scrape_toto.py        # Scraper script dedicated to Sports Toto
├── start_bot.bat         # Batch script to easily launch the bot on Windows
├── data/                 # Directory where CSV result datasets are stored
├── debug_samples/        # Folder for debugging scraping responses
└── sounds/               # Directory containing audio files for bot replies
```

## 🛠 Prerequisites

Before running the bot, ensure you have the following installed:
- **Python 3.9+** (With built-in zoneinfo and asyncio support)
- **Git** (If you intend to use the Admin GitHub backup feature)

## ⚙️ Installation & Setup

Choose the installation and setup steps below corresponding to your operating system.

### Windows Installation

1. **Clone the repository:**
   ```powershell
   git clone https://github.com/lck920/randai-scraper-bot.git
   cd randai-scraper-bot
   ```

2. **Install Required Packages:**
   ```powershell
   pip install "python-telegram-bot[job-queue]>=20.0" requests beautifulsoup4
   ```
   > **Note:** The `[job-queue]` extra dependency is required to enable the daily automatic 9 PM job scheduling in the bot.

---

### macOS & Linux Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/lck920/randai-scraper-bot.git
   cd randai-scraper-bot
   ```

2. **Create and Activate a Virtual Environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Required Packages:**
   ```bash
   pip3 install "python-telegram-bot[job-queue]>=20.0" requests beautifulsoup4
   ```

---

## 🔑 Configuration & Verification

The bot expects two environment variables to function properly:
- `RAND_AI_BOT_TOKEN` — Your Telegram Bot Token.
- `RAND_AI_ADMIN_CHAT_ID` — Your Telegram numeric User ID.

Create a copy of the `.env.example` file, rename it to `.env`, and populate your credentials:
```ini
RAND_AI_BOT_TOKEN="your_telegram_bot_token_here"
RAND_AI_ADMIN_CHAT_ID="your_personal_chat_id_here"
```
> **Tip:** You can get your bot token by creating a bot through the [@BotFather](https://t.me/BotFather) on Telegram. To find your Chat ID, you can message [@userinfobot](https://t.me/userinfobot).

If you are running the bot in environments where system environment variables are preferred, follow the guides below to set up and verify the configuration.

### Setup in Windows PowerShell

1. **Set Environment Variables:**
   ```powershell
   $env:RAND_AI_BOT_TOKEN="your_bot_token_here"
   $env:RAND_AI_ADMIN_CHAT_ID="your_chat_id_here"
   ```

2. **Verify Configuration:**
   ```powershell
   $env:RAND_AI_BOT_TOKEN
   $env:RAND_AI_ADMIN_CHAT_ID
   ```
   Ensure the output matches your actual token and chat ID.

### Setup in macOS & Linux (Bash / Zsh)

1. **Set Environment Variables:**
   ```bash
   export RAND_AI_BOT_TOKEN="your_bot_token_here"
   export RAND_AI_ADMIN_CHAT_ID="your_chat_id_here"
   ```

2. **Verify Configuration:**
   ```bash
   echo $RAND_AI_BOT_TOKEN
   echo $RAND_AI_ADMIN_CHAT_ID
   ```

3. **Permanent Configuration (Optional):**
   To make these variables persistent, append them to your shell profile file (e.g., `~/.bashrc` or `~/.zshrc`):
   ```bash
   echo 'export RAND_AI_BOT_TOKEN="your_bot_token_here"' >> ~/.zshrc
   echo 'export RAND_AI_ADMIN_CHAT_ID="your_chat_id_here"' >> ~/.zshrc
   source ~/.zshrc
   ```

---

## 🚀 Usage

### 1. Running the Telegram Bot
To start the bot so it can actively listen for Telegram commands and run its scheduled updates:

- **On Windows (Shortcut):** Double-click the `start_bot.bat` file. This script launches the bot in an automatic crash recovery loop—if the bot stops due to connection issues, it restarts after 5 seconds automatically.
- **On Windows (Manual):** 
  ```powershell
  python bot.py
  ```
- **On macOS & Linux:**
  ```bash
  python3 bot.py
  ```

### 2. Manual Scraping (Standalone)
One of the key strengths of this codebase is that the scraping modules can be run completely independently of the Telegram bot. If you do not want to run the full Telegram bot interface and just want to update the local datasets immediately, you can run the scraper scripts manually.

**On Windows (PowerShell):**
```powershell
# Scrape or update SportsToto 4D results manually
python scrape_toto.py

# Scrape or update Magnum 4D results manually
python scrape_magnum.py
```

**On macOS / Linux:**
```bash
# Scrape or update SportsToto 4D results manually
python3 scrape_toto.py

# Scrape or update Magnum 4D results manually
python3 scrape_magnum.py
```

#### Standalone Scraper Features:
- **Zero-Configuration Mode:** The scrapers do not require Telegram Bot tokens or environment variables to be set. They are completely decoupled.
- **Back-Scraping from 1985:** If no local CSV dataset is detected in the `data/` folder, the script automatically initializes a full historical scrape going all the way back to **January 1, 1985**.
- **Smart Incremental Updates:** If an existing dataset is detected, the script reads the latest draw date present in the file and only scrapes dates from the last **14 days** to today. This updates missing/recent rows instantly while preventing duplicate requests.
- **Auto-Cleanup:** The SportsToto scraper automatically removes outdated CSV files once a new one is saved, keeping the `data/` directory tidy and containing only the most up-to-date compiled dataset.

---

## 💬 Bot Commands

### User Commands
- `/start` - Start the bot and see the main menu.
- `/subscribe` - Subscribe to automatic result notifications and data updates.
- `/unsubscribe` - Stop receiving automatic result updates.
- `/update` - Force the bot to immediately scrape and pull the latest results.
- `/result` - Show the latest locally saved results.
- `/search [1234]` - Search if a specific 4-digit number has appeared in past draws.
- `/hot` - Display the most frequently drawn numbers recently.
- `/cold` - Display the least frequently drawn numbers recently.
- `/stats` - View statistics regarding the currently stored datasets.
- `/help` - View the help manual.

### Admin Commands
- `/backup` - Pushes the latest code and dataset CSVs to the configured GitHub repository.
- `/admincheck` - Verifies if you have administrator privileges.

---

## ⚠️ Disclaimer

This project is for educational and experimental purposes only. Number analysis algorithms like the hot/cold commands do not guarantee future results. Play responsibly!

## 📝 License

Developed by [lck920](https://github.com/lck920). All rights reserved.
