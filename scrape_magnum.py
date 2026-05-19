"""
Scraper script for Magnum 4D results from 4dmoon.com.
This script fetches past results, parses them, and saves them to a CSV file.
"""
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
    """
    Pads a given string value to ensure it is exactly 4 digits long.
    Strips non-digit characters and prepends zeros if necessary.
    """
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

    # Find only the Magnum 4D box, not the whole page
    magnum_box = None

    for box in soup.select("div.mbx"):
        text = box.get_text(" ", strip=True)

        if "Magnum 4D" in text and "Magnum 4D Jackpot" not in text:
            magnum_box = box
            break

    if not magnum_box:
        return None

    text = magnum_box.get_text(" ", strip=True)

    # Draw no, example: #369/26
    draw_match = re.search(r"#\s*([0-9]+/[0-9]+)", text)
    draw_no = draw_match.group(1) if draw_match else ""

    row = {col: "" for col in CSV_COLUMNS}
    row["date"] = draw_date.strftime("%d-%m-%Y")
    row["drawno"] = draw_no

    # Latest/current page uses IDs: MP1, MP2, MP3, MS1..MS13, MC1..MC10
    if magnum_box.select_one("#MP1"):
        row["winning1"] = pad4(magnum_box.select_one("#MP1").get_text(strip=True))
        row["winning2"] = pad4(magnum_box.select_one("#MP2").get_text(strip=True))
        row["winning3"] = pad4(magnum_box.select_one("#MP3").get_text(strip=True))

        special_nums = []
        for i in range(1, 14):
            el = magnum_box.select_one(f"#MS{i}")
            if el:
                num = pad4(el.get_text(strip=True))
                if num:
                    special_nums.append(num)

        consolation_nums = []
        for i in range(1, 11):
            el = magnum_box.select_one(f"#MC{i}")
            if el:
                num = pad4(el.get_text(strip=True))
                if num:
                    consolation_nums.append(num)

    else:
        # Past page format: prize numbers are inside class rtn
        prize_cells = magnum_box.select("td.rtn")
        if len(prize_cells) < 3:
            return None

        row["winning1"] = pad4(prize_cells[0].get_text(strip=True))
        row["winning2"] = pad4(prize_cells[1].get_text(strip=True))
        row["winning3"] = pad4(prize_cells[2].get_text(strip=True))

        special_nums = []
        consolation_nums = []

        tables = magnum_box.select("table.rtb2")

        for table in tables:
            table_text = table.get_text(" ", strip=True)

            if "Special" in table_text:
                for cell in table.select("td.rbn"):
                    num = pad4(cell.get_text(strip=True))
                    if num:
                        special_nums.append(num)

            elif "Consolation" in table_text:
                for cell in table.select("td.rbn"):
                    num = pad4(cell.get_text(strip=True))
                    if num:
                        consolation_nums.append(num)

    special_nums = (special_nums + [""] * 10)[:10]
    consolation_nums = (consolation_nums + [""] * 10)[:10]

    for i in range(10):
        row[f"special{i + 1}"] = special_nums[i]
        row[f"consolation{i + 1}"] = consolation_nums[i]

    if not row["winning1"] or not row["winning2"] or not row["winning3"]:
        return None

    return row


def write_csv(rows, path):
    rows.sort(key=lambda r: parse_date_from_csv(r["date"]))

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    """
    Main execution function.
    Checks for an existing dataset, determines the date range to scrape,
    fetches new results concurrently, and saves the updated dataset.
    """
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