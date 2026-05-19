# 4DMoon Lottery Scraper (Magnum & Toto)

This repository contains Python scripts designed to scrape historical and current 4D lottery results for **Magnum 4D** and **SportsToto 4D** from [4dmoon.com](https://www.4dmoon.com). The extracted data is automatically merged and exported into structured CSV files for analysis.

## Features

- **Automated Data Extraction:** Scrapes draw dates, draw numbers, top 3 prizes, special numbers, and consolation numbers.
- **Multithreaded Scraping:** Uses `ThreadPoolExecutor` to fetch missing dates concurrently for faster extraction.
- **Smart Resuming:** Automatically finds the most recent CSV file and resumes scraping from the last recorded date (or goes back 60 days to recheck). If no file exists, it can fetch historical data dating back to 1985.
- **Data Validation & Repair:** Automatically detects suspicious or malformed rows (e.g., mislabelled 2D/3D results from the website) and repairs them in subsequent runs.
- **Clean Output:** Outputs to neatly formatted CSV files and automatically cleans up older CSV versions to save space.

## Project Structure

- `scrape_magnum.py` - Main script to scrape Magnum 4D results. Outputs to `magnum_pastresult_DDMMYY.csv`.
- `scrape_toto.py` - Main script to scrape SportsToto 4D results. Outputs to `toto_pastresult_DDMMYY.csv`.
- `debug_samples/` - A directory containing raw HTML snippets of the 4dmoon tables. These files are kept for reference and troubleshooting in case the website's layout changes.

## Prerequisites

Before running the scripts, ensure you have Python 3 installed along with the following packages:

```bash
pip install requests beautifulsoup4
```

## Usage

To run the Magnum scraper:
```bash
python scrape_magnum.py
```

To run the Toto scraper:
```bash
python scrape_toto.py
```

On the first run, the scripts will attempt to fetch data from scratch. On subsequent runs, they will detect the existing CSV files and only download the newly added draws.

## Disclaimer

This project is for educational and data analysis purposes only. Please respect the terms of service of the scraped website and use appropriate request delays.
