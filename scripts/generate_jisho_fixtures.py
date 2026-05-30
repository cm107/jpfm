#!/usr/bin/env python3
"""
Script to generate Jisho.org HTML fixtures for testing.

This script fetches real HTML from Jisho.org and caches it locally
in tests/fixtures/jisho/current/ for use in fixture-based tests.

Run this script when you want to update or create new test fixtures:
    python scripts/generate_jisho_fixtures.py
"""

import time
from pathlib import Path
from typing import List
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import quote

# Test words to fetch: variety of word types
TEST_WORDS = [
    "食べる",  # Simple verb (taberu - to eat)
    "本",      # Simple noun (hon - book)
    "走る",    # Action verb (hashiru - to run)
    "水",      # Simple noun (mizu - water)
    "赤い",    # i-adjective (akai - red)
]

# URL to fetch (will append word as query parameter)
JISHO_BASE_URL = "https://jisho.org/search/"

# Output directory
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "jisho" / "current"

def fetch_jisho_html(word: str) -> str:
    """
    Fetch HTML from Jisho.org for a given word.

    Args:
        word: Japanese word to search for.

    Returns:
        str: Raw HTML content from Jisho.org.

    Raises:
        URLError: If the request fails.
    """
    # URL-encode the word to handle Japanese characters properly
    encoded_word = quote(word.encode("utf-8"))
    url = f"{JISHO_BASE_URL}{encoded_word}"
    print(f"Fetching: {url}")
    
    try:
        with urlopen(url, timeout=10) as response:
            html = response.read().decode("utf-8")
            print(f"  ✓ Successfully fetched {len(html)} bytes")
            return html
    except HTTPError as e:
        print(f"  ✗ HTTP Error {e.code}: {e.reason}")
        raise
    except URLError as e:
        print(f"  ✗ URL Error: {e.reason}")
        raise


def save_fixture(word: str, html: str) -> Path:
    """
    Save HTML fixture to a file.

    Args:
        word: Japanese word (used for filename).
        html: Raw HTML content.

    Returns:
        Path: Path to saved fixture file.
    """
    # Convert word to a valid filename (romanized or hex-encoded)
    # For simplicity, use the word directly as the filename (safe on modern filesystems)
    filename = f"{word}.html"
    filepath = FIXTURES_DIR / filename
    
    filepath.write_text(html, encoding="utf-8")
    print(f"  ✓ Saved to {filepath}")
    
    return filepath


def main() -> None:
    """Generate Jisho.org test fixtures."""
    print("JPFM: Generating Jisho.org Test Fixtures\n")
    
    # Create fixtures directory
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Fixtures directory: {FIXTURES_DIR}\n")
    
    successful = 0
    failed = 0
    
    for word in TEST_WORDS:
        try:
            html = fetch_jisho_html(word)
            save_fixture(word, html)
            successful += 1
            
            # Be respectful: wait between requests to avoid rate limiting
            time.sleep(1)
        except Exception as e:
            print(f"  ✗ Failed to generate fixture for '{word}': {e}\n")
            failed += 1
            continue
    
    print(f"\n✓ Generated {successful} fixtures")
    if failed > 0:
        print(f"✗ Failed to generate {failed} fixtures")
    
    if successful > 0:
        print(f"\nFixtures saved to: {FIXTURES_DIR}")


if __name__ == "__main__":
    main()
