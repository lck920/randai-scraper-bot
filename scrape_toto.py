import csv
import glob
import os
import re
import time
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.4dmoon.com/past-results/{}"

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

PREFIX = "toto"
GAME_NAME = "SportsToto 4D"

FALLBACK_START_DATE = date(1985, 1, 1)
RECHECK_DAYS = 14

MAX_WORKERS = 10
REQUEST_TIMEOUT = 20
RETRY_COUNT = 2
SLEEP_BETWEEN_RETRIES = 0.8

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; Win64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    )
}

CSV_COLUMNS = [
    "date", "drawno",
    "winning1", "winning2", "winning3",
    "special1", "special2", "special3", "special4", "special5",
    "special6", "special7", "special8", "special9", "special10",
    "consolation1", "consolation2", "consolation3", "consolation4", "consolation5",
    "consolation6", "consolation7", "consolation8", "consolation9", "consolation10",
]


def pad4(value):
    value = str(value).strip()
    if value == "----" or not value:
        return ""

    digits = re.sub(r"\D", "", value)
    if not digits:
        return ""

    return digits.zfill(4)[-4:]


def parse_date_from_csv(date_text):
    return datetime.strptime(date_text, "%d-%m-%Y").date()


def daterange(start, end):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def find_latest_csv():
    files = glob.glob(os.path.join(DATA_DIR, f"{PREFIX}_pastresult_*.csv"))

    if not files:
        return None

    return max(files, key=os.path.getmtime)


def load_existing_csv(path):
    rows = []
    latest = None

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
    main()