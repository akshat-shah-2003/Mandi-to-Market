import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv("DATA_URL")
API_KEY = os.getenv("DATASET_API_KEY")

LIMIT = 1000
MAX_RETRIES = 3
RETRY_DELAY = 2
BATCH_DELAY = 0.5

OUTPUT_DIR = Path("data/raw/mandi_prices")
HEADERS = {"User-Agent": "Mandi-to-Market/1.0"}

session = requests.Session()
session.headers.update(HEADERS)


def fetch_batch(state: str, offset: int) -> list[dict]:
    """Fetch one batch of records for a state, retrying on network errors."""
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": LIMIT,
        "offset": offset,
        "filters[state.keyword]": state,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(URL, params=params, timeout=30)
            response.raise_for_status()
            return response.json().get("records", [])
        except (requests.RequestException, ValueError) as e:
            print(f"  Attempt {attempt}/{MAX_RETRIES} failed at offset {offset}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    raise RuntimeError(f"Failed to fetch {state} at offset {offset}")


def fetch_all_records(state: str) -> list[dict]:
    """Fetch all records for a state using offset-based pagination."""
    if not URL or not API_KEY:
        raise RuntimeError("DATA_URL and DATASET_API_KEY must be set in .env")

    all_records = []
    offset = 0

    while True:
        records = fetch_batch(state, offset)
        all_records.extend(records)
        print(f"  offset {offset}: {len(records)} records (total {len(all_records)})")

        # A short batch means we've reached the end of the dataset.
        if len(records) < LIMIT:
            return all_records

        offset += LIMIT
        time.sleep(BATCH_DELAY)


def save_records(records: list[dict], state: str) -> Path:
    """Save raw records for a state to data/raw/mandi_prices/<state>.json."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"{state.lower().replace(' ', '_')}_mandi_prices.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=2, ensure_ascii=False)

    print(f"  saved {len(records)} records -> {output_file}")
    return output_file


def ingest_state(state: str) -> int:
    """Fetch and save every record for one state. Returns the record count."""
    print(f"\n{state}")
    records = fetch_all_records(state)
    save_records(records, state)
    return len(records)


if __name__ == "__main__":
    ingest_state("Madhya Pradesh")
