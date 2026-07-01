"""Download the XMLTV EPG feed and save it locally as raw_epg.xml."""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

EPG_URL = os.getenv("EPG_URL")
OUTPUT_PATH = "raw_epg.xml"
PREVIEW_CHARS = 2000


def download_epg(url: str) -> bytes:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.content


def save_epg(data: bytes, path: str) -> None:
    with open(path, "wb") as f:
        f.write(data)


def main():
    print(f"Downloading EPG from: {EPG_URL}")
    raw = download_epg(EPG_URL)
    print(f"Downloaded {len(raw):,} bytes")

    preview = raw[:PREVIEW_CHARS].decode("utf-8", errors="replace")
    print(f"\n--- First {PREVIEW_CHARS} characters of raw XML ---\n")
    print(preview)
    print("\n--- end preview ---")

    save_epg(raw, OUTPUT_PATH)
    print(f"\nSaved full XML to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()