# RandAI Telegram Bot

[![Bot Status](https://img.shields.io/badge/Status-Online-success.svg)](#)

**RandAI (@RandAI_bot)** is an intelligent, lazy-but-useful Telegram bot that scrapes, auto-sorts, and notifies users of Toto and Magnum 4D lottery results. The bot manages datasets locally in CSV format, provides detailed historical number analysis (hot/cold numbers), allows users to search for past numbers, and offers a manual backup mechanism for administrators.

## 🚀 Features

- **Automated Data Scraping:** Retrieves the latest Toto & Magnum 4D results directly from 4dmoon.
- **Multi-user Subscription System:** Users can subscribe via Telegram to receive automatic result updates as soon as they drop.
- **Smart Analytics:** Analyze datasets to display the "hottest" (most frequently drawn) and "coldest" (least frequently drawn) numbers.
- **Search History:** Query specific 4-digit numbers to see exactly when and where they appeared in past draws.
- **Scheduled Auto-Updates:** Built-in auto-checking at 9 PM (Malaysia Time) for timely notification drops.
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
- **Python 3.9+**
- Required Python libraries (can be installed via pip):
  ```bash
  pip install python-telegram-bot
  ```
- **Git** (If you intend to use the Admin GitHub backup feature)

## ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/lck920/randai-scraper-bot.git
   cd randai-scraper-bot
   ```

2. **Configure Environment Variables:**
   - Create a copy of the `.env.example` file and rename it to `.env`.
   - Fill in your sensitive credentials (or set them directly in your system environment):
   ```ini
   RAND_AI_BOT_TOKEN="your_telegram_bot_token_here"
   RAND_AI_ADMIN_CHAT_ID="your_personal_chat_id_here"
   ```
   > **Tip:** You can get your bot token by creating a bot through the [@BotFather](https://t.me/BotFather) on Telegram. To find your Chat ID, you can message [@userinfobot](https://t.me/userinfobot).

3. **Verify Configuration:**
   - Ensure the `.env` file is located in the root directory alongside `bot.py`.
   - Ensure the `data/` and `sounds/` directories exist (though the bot will try to manage files accordingly, verifying their presence avoids early crashes).

## 🚀 Usage

### 1. Running the Telegram Bot
To start the bot so it can actively listen for Telegram commands and run its scheduled updates:
- **On Windows:** Simply double-click the `start_bot.bat` file.
- **Via Terminal:** 
  ```bash
  python bot.py
  ```

### 2. Manual Scraping (Standalone)
If you do not want to run the full Telegram bot interface and just want to update the local datasets immediately, you can run the scraper scripts independently:
```bash
# Scrape or update the Magnum 4D dataset manually
python scrape_magnum.py

# Scrape or update the Sports Toto dataset manually
python scrape_toto.py
```
These standalone scripts will parse the latest pages and update the CSV files directly inside the `data/` folder.

## 💬 Bot Commands

### User Commands
- `/start` - Start the bot and see the main menu.
- `/subscribe` - Subscribe to automatic Toto & Magnum result notifications.
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

## ⚠️ Disclaimer

This project is for educational and experimental purposes only. Number analysis algorithms like the hot/cold commands do not guarantee future results. Play responsibly!

## 📝 License

Developed by [lck920](https://github.com/lck920). All rights reserved.
