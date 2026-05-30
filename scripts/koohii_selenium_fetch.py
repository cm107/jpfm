#!/usr/bin/env python3
"""
Selenium-based Koohii fetcher.

This script uses Selenium with Chrome (headless) to log in to Kanji Koohii
and fetch kanji pages, saving the rendered HTML to
`tests/fixtures/koohii/current/` for use as fixtures.

Requirements (install locally):
- Google Chrome or Chromium
- chromedriver matching the browser version, or use webdriver-manager
- Python packages: selenium, webdriver-manager, beautifulsoup4, python-dotenv

Usage:
    python scripts/koohii_selenium_fetch.py --words 愛 行 音

Security: Credentials are read from environment variables `KOOHII_USER` and
`KOOHII_PASS`, or from `docs/koohii_login_info.md` if present. After successful
fetching, credentials are saved to `.env` and the docs file is removed.
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

# Try imports for selenium; fail gracefully if not installed
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoSuchElementException, WebDriverException
    from webdriver_manager.chrome import ChromeDriverManager
except Exception:
    webdriver = None


DOCS_CREDS = Path(__file__).parent.parent / "docs" / "koohii_login_info.md"
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "koohii" / "current"
BACKUP_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "koohii" / "backup"
ENV_FILE = Path(__file__).parent.parent / ".env"


def read_creds_from_env() -> Optional[Dict[str, str]]:
    user = os.environ.get("KOOHII_USER")
    pwd = os.environ.get("KOOHII_PASS")
    if user and pwd:
        return {"username": user, "password": pwd}
    return None


def read_creds_from_docs() -> Optional[Dict[str, str]]:
    if not DOCS_CREDS.exists():
        return None
    text = DOCS_CREDS.read_text(encoding="utf-8")
    user_match = re.search(r"Username:\s*(\S+)", text)
    pass_match = re.search(r"Password:\s*(\S+)", text)
    if user_match and pass_match:
        return {"username": user_match.group(1), "password": pass_match.group(1)}
    return None


def save_env(creds: Dict[str, str]) -> None:
    content = f"KOOHII_USER={creds['username']}\nKOOHII_PASS={creds['password']}\n"
    ENV_FILE.write_text(content, encoding="utf-8")
    print(f"Wrote credentials to {ENV_FILE}")
    # Add .env to .gitignore if not present
    gitignore = Path(__file__).parent.parent / ".gitignore"
    if gitignore.exists():
        txt = gitignore.read_text(encoding="utf-8")
        if ".env" not in txt:
            gitignore.write_text(txt + "\n.env\n", encoding="utf-8")
            print("Appended .env to .gitignore")
    else:
        gitignore.write_text(".env\n", encoding="utf-8")
        print("Created .gitignore and added .env")


def remove_docs_creds():
    if DOCS_CREDS.exists():
        DOCS_CREDS.unlink()
        print(f"Removed docs credentials file: {DOCS_CREDS}")


def launch_browser(headless: bool = True):
    if webdriver is None:
        raise RuntimeError("selenium or webdriver-manager not installed in this environment")
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1200,800")
    # Use webdriver-manager to get chromedriver
    try:
        driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    except TypeError:
        # older selenium signature
        driver = webdriver.Chrome(ChromeDriverManager().install(), chrome_options=options)
    return driver


def login_koohii(driver, username: str, password: str, timeout: int = 10) -> bool:
    # Navigate to account page and fill the form
    login_url = 'https://kanji.koohii.com/account'
    driver.get(login_url)
    time.sleep(1)
    try:
        # Try common field identifiers
        try:
            user_input = driver.find_element(By.NAME, 'username')
        except NoSuchElementException:
            try:
                user_input = driver.find_element(By.ID, 'username')
            except NoSuchElementException:
                # fallback: find input[type=text]
                user_input = driver.find_element(By.CSS_SELECTOR, 'input[type=text]')
        try:
            pass_input = driver.find_element(By.NAME, 'password')
        except NoSuchElementException:
            try:
                pass_input = driver.find_element(By.ID, 'password')
            except NoSuchElementException:
                pass_input = driver.find_element(By.CSS_SELECTOR, 'input[type=password]')

        user_input.clear()
        user_input.send_keys(username)
        pass_input.clear()
        pass_input.send_keys(password)

        # Try to click Sign In button
        try:
            btn = driver.find_element(By.XPATH, "//button[contains(., 'Sign In') or contains(., 'Sign in')]")
            btn.click()
        except NoSuchElementException:
            try:
                btn = driver.find_element(By.XPATH, "//input[@type='submit']")
                btn.click()
            except NoSuchElementException:
                # last resort: submit the form
                pass_input.submit()

        # Wait for navigation
        time.sleep(2)
        # Heuristic: check title or presence of logout/profile
        page = driver.page_source.lower()
        if 'logout' in page or 'sign out' in page or 'kanji koohii' in driver.title:
            return True
        return False
    except Exception as e:
        print("Login exception:", e)
        return False


def fetch_kanji_page(driver, kanji: str) -> Optional[str]:
    # use study/kanji path per legacy implementation
    url = f'https://kanji.koohii.com/study/kanji/{kanji}'
    driver.get(url)
    time.sleep(1)
    return driver.page_source


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--words', nargs='*', default=['愛','行','音'])
    parser.add_argument('--headless', action='store_true', default=True)
    parser.add_argument('--use-docs-creds', action='store_true')
    args = parser.parse_args(argv)

    creds = read_creds_from_env() or (read_creds_from_docs() if args.use_docs_creds else None)
    if not creds:
        print('Credentials not found in environment or docs file. Provide KOOHII_USER/KOOHII_PASS or use --use-docs-creds')
        return 2

    try:
        driver = launch_browser(headless=args.headless)
    except Exception as e:
        print('Failed to start browser:', e)
        print('Ensure selenium, webdriver-manager and a compatible Chrome/Chromedriver are installed.')
        return 3

    try:
        ok = login_koohii(driver, creds['username'], creds['password'])
        if not ok:
            print('Login failed (selenium heuristic)')
            return 4
        print('Login successful')
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        for w in args.words:
            html = fetch_kanji_page(driver, w)
            if html and len(html) > 1000:
                path = FIXTURES_DIR / f"{w}.html"
                path.write_text(html, encoding='utf-8')
                print('Saved', path)
            else:
                print('Failed to fetch or short HTML for', w)
        # Save creds and secure
        save_env(creds)
        remove_docs_creds()
        return 0
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == '__main__':
    raise SystemExit(main())
