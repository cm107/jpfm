#!/usr/bin/env python3
"""
Script to generate Kotobank HTML fixtures for testing.

Saves fixtures to `tests/fixtures/kotobank/current/`.
"""

import time
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import quote
from urllib.error import URLError, HTTPError

TEST_WORDS = [
    "漢字",
    "日本",
    "東京",
]

KOTOBANK_BASE = "https://kotobank.jp/word/"
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "kotobank" / "current"


def fetch_kotobank_html(word: str) -> str:
    encoded = quote(word.encode("utf-8"))
    url = f"{KOTOBANK_BASE}{encoded}"
    print(f"Fetching: {url}")
    with urlopen(url, timeout=15) as resp:
        html = resp.read().decode("utf-8")
        print(f"  ✓ Fetched {len(html)} bytes")
        return html


def save_fixture(word: str, html: str) -> Path:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    filepath = FIXTURES_DIR / f"{word}.html"
    filepath.write_text(html, encoding="utf-8")
    print(f"  ✓ Saved to {filepath}")
    return filepath


def main():
    print("Generating Kotobank fixtures")
    success = 0
    fail = 0
    for w in TEST_WORDS:
        try:
            html = fetch_kotobank_html(w)
            save_fixture(w, html)
            success += 1
            time.sleep(1)
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            fail += 1
    print(f"Done: {success} success, {fail} failed")


if __name__ == '__main__':
    main()
