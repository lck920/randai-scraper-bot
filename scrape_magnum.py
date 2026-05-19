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

PREFIX = "magnum"
GAME_NAME = "Magnum 4D"

FALLBACK_START_DATE = date(1985, 1, 1)
RECHECK_DAYS = 14

MAX_WORKERS = 10
REQUEST_TIMEOUT = 20
RETRY_COUNT = 2
SLEEP_BETWEEN_RETRIES = 0.8

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
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
    return digits.zfill(4)[-4:] if digits else ""


def parse_date_from_csv(date_text):
    return datetime.strptime(date_text, "%d-%m-%Y").date()


def daterange(start, end):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def find_latest_csv():
    files = glob.glob(os.path.join(DATA_DIR, f"{PREFIX}_pastresult_*.csv"))
    return max(files, key=os.path.getmtime) if files else None


def load_existing_csv(path):
    rows = []
    latest = None

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            fixed = {col: row.get(col, "") for col in CSV_COLUMNS}
            rows.append(fixed)

            try:
                d = parse_date_from_csv(fixed["date"])
                if latest is None or d > latest:
                    latest = d
            except Exception:
                pass

    return rows, latest


def latest_output_filename(rows):
    latest = None

    for row in rows:
        try:
            d = parse_date_from_csv(row["date"])
            if latest is None or d > latest:
                latest = d
        except Exception:
            pass

    if latest is None:
        latest = date.today()

    return os.path.join(DATA_DIR, f"{PREFIX}_pastresult_{latest.strftime('%d%m%y')}.csv")


def get_html(url):
    for attempt in range(RETRY_COUNT + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

            if response.status_code == 200:
                return response.text

            if response.status_code == 404:
                return None

        except requests.RequestException:
            pass

        if attempt < RETRY_COUNT:
            time.sleep(SLEEP_BETWEEN_RETRIES)

    return None


def extract_numbers(text):
    return re.findall(r"\b\d{4}\b", text)


def scrape_date(draw_date):
    url = BASE_URL.format(draw_date.strftime("%Y-%m-%d"))
    html = get_html(url)

    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    if GAME_NAME.lower() not in page_text.lower():
        return None

    numbers = extract_numbers(page_text)

    if len(numbers) < 23:
        return None

    row = {col: "" for col in CSV_COLUMNS}

    row["date"] = draw_date.strftime("%d-%m-%Y")
    row["drawno"] = ""

    row["winning1"] = pad4(numbers[0])
    row["winning2"] = pad4(numbers[1])
    row["winning3"] = pad4(numbers[2])

    idx = 3

    for i in range(1, 11):
        row[f"special{i}"] = pad4(numbers[idx])
        idx += 1

    for i in range(1, 11):
        row[f"consolation{i}"] = pad4(numbers[idx])
        idx += 1

    return row


def write_csv(rows, path):
    rows.sort(key=lambda r: parse_date_from_csv(r["date"]))

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    existing_file = find_latest_csv()
    existing_rows = []

    if existing_file:
        existing_rows, latest_date = load_existing_csv(existing_file)

        print(f"Found existing {GAME_NAME} dataset: {os.path.basename(existing_file)}")
        print(f"  Loaded {len(existing_rows)} rows. Latest draw date in file: {latest_date}")

        start_date = latest_date - timedelta(days=RECHECK_DAYS)
    else:
        print(f"No local dataset found for {GAME_NAME}.")
        start_date = FALLBACK_START_DATE

    end_date = date.today()
    dates = list(daterange(start_date, end_date))

    print(f"Fetching/checking {len(dates)} date(s) from 4dmoon...")

    rows_by_date = {row["date"]: row for row in existing_rows}
    new_rows = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {executor.submit(scrape_date, d): d for d in dates}

        count = 0

        for future in as_completed(future_map):
            count += 1
            d = future_map[future]

            try:
                row = future.result()

                if row:
                    rows_by_date[row["date"]] = row
                    new_rows.append(row)

                    print(
                        f"  [{count}/{len(dates)}] OK   {row['date']} "
                        f"{row['winning1']} {row['winning2']} {row['winning3']}"
                    )
                else:
                    print(
                        f"  [{count}/{len(dates)}] SKIP {d} "
                        f"(no draw / no valid {GAME_NAME} data)"
                    )

            except Exception as e:
                print(f"  ERROR {d}: {e}")

    all_rows = list(rows_by_date.values())
    out = latest_output_filename(all_rows)

    write_csv(all_rows, out)

    print(
        f"\nSaved {len(all_rows)} total rows "
        f"({len(new_rows)} scraped/updated) -> {os.path.basename(out)}"
    )


if __name__ == "__main__":
    main()