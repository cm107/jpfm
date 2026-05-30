#!/usr/bin/env python3
"""
Login to Koohii and fetch live pages to generate fixtures.

Usage:
    python scripts/koohii_login_and_fetch.py --words 愛 行 音

This script attempts to discover the login form on common Koohii hosts,
submits credentials, and fetches the requested pages saving them to
`tests/fixtures/koohii/current/` (backing up existing files first).

Credentials source (in order):
- Environment variables: `KOOHII_USER`, `KOOHII_PASS`
- `docs/koohii_login_info.md` file with lines 'Username: ...' and 'Password: ...'

Security: After successful authentication and fetching, the script will
create a `.env` file containing the credentials and will delete
`docs/koohii_login_info.md` to avoid committing credentials accidentally.
Make sure you have a backup if needed.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup


CANDIDATE_LOGIN_URLS = [
    "https://kanji.koohii.com/login",
    "https://kanji.koohii.com/",  # sometimes has modal
    "https://koohii.com/login",
    "https://koohii.com/",
]

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "koohii" / "current"
BACKUP_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "koohii" / "backup"
DOCS_CREDS = Path(__file__).parent.parent / "docs" / "koohii_login_info.md"
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


def discover_login_form(session: requests.Session, url: str) -> Optional[Dict]:
    try:
        r = session.get(url, timeout=15)
    except Exception:
        return None
    if r.status_code >= 400:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    # Find forms that look like login forms
    for form in soup.find_all("form"):
        form_text = form.get_text(" ", strip=True).lower()
        if "login" in form_text or form.find("input", attrs={"type": "password"}):
            action = form.get("action") or url
            method = (form.get("method") or "post").lower()
            inputs = {}
            for inp in form.find_all("input"):
                name = inp.get("name")
                if not name:
                    continue
                value = inp.get("value", "")
                inputs[name] = value
            return {"action": requests.compat.urljoin(r.url, action), "method": method, "inputs": inputs}
    return None


def attempt_login(session: requests.Session, creds: Dict[str, str]) -> bool:
    # Try candidate URLs and try to find a login form
    for url in CANDIDATE_LOGIN_URLS:
        form = discover_login_form(session, url)
        if not form:
            continue
        action = form["action"]
        inputs = form["inputs"].copy()
        # Find probable username and password field names
        uname_field = None
        pwd_field = None
        for name in inputs.keys():
            low = name.lower()
            if "user" in low or "login" in low or "email" in low:
                uname_field = name
            if "pass" in low:
                pwd_field = name
        # Fallback names
        if not uname_field:
            for cand in ("username", "user", "login", "email"):
                if cand in inputs:
                    uname_field = cand
                    break
        if not pwd_field:
            for cand in ("password", "passwd", "pass"):
                if cand in inputs:
                    pwd_field = cand
                    break
        if not uname_field or not pwd_field:
            # Try to infer by input types
            for inp in inputs:
                # nothing to do, already captured
                pass
        payload = {}
        payload.update(inputs)
        if uname_field:
            payload[uname_field] = creds["username"]
        else:
            # inject common field names
            payload["username"] = creds["username"]
        if pwd_field:
            payload[pwd_field] = creds["password"]
        else:
            payload["password"] = creds["password"]
        try:
            if form["method"] == "post":
                resp = session.post(action, data=payload, timeout=15)
            else:
                resp = session.get(action, params=payload, timeout=15)
        except Exception:
            continue
        # Heuristic: if response sets a session cookie or redirect to dashboard
        if resp.status_code in (200, 302):
            # Check for presence of 'logout' or 'profile' links
            txt = resp.text.lower()
            if "logout" in txt or "sign out" in txt or "profile" in txt or resp.history:
                return True
            # Also check cookies
            if session.cookies:
                return True
    return False


def fetch_pages(session: requests.Session, words: List[str], out_dir: Path) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: List[Path] = []
    for w in words:
        # Build URL - Koohii kanji pages often at https://kanji.koohii.com/kanji/<char>
        urls = [
            f"https://kanji.koohii.com/kanji/{w}",
            f"https://kanji.koohii.com/kanji/{w}/",
            f"https://koohii.com/kanji/{w}",
        ]
        fetched = False
        for url in urls:
            try:
                r = session.get(url, timeout=15)
            except Exception:
                continue
            if r.status_code == 200 and len(r.text) > 500:
                fname = out_dir / f"{w}.html"
                fname.write_text(r.text, encoding="utf-8")
                print(f"Saved {fname}")
                saved.append(fname)
                fetched = True
                break
        if not fetched:
            print(f"Failed to fetch live page for {w}")
    return saved


def backup_existing(fixtures_dir: Path, backup_dir: Path) -> None:
    if not fixtures_dir.exists():
        return
    backup_dir.mkdir(parents=True, exist_ok=True)
    for f in fixtures_dir.glob("*.html"):
        target = backup_dir / f.name
        if not target.exists():
            f.rename(target)
            print(f"Backed up {f} -> {target}")


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


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--words", nargs="*", help="Words to fetch (kanji characters)", default=["愛", "行", "音"])
    p.add_argument("--use-docs-creds", action="store_true", help="Force use of docs/koohii_login_info.md for credentials")
    args = p.parse_args(argv)

    creds = read_creds_from_env()
    if not creds and (args.use_docs_creds or DOCS_CREDS.exists()):
        creds = read_creds_from_docs()
    if not creds:
        print("Credentials not found in environment or docs/koohii_login_info.md. Aborting.")
        return 2

    session = requests.Session()
    print("Attempting login to Koohii...")
    ok = attempt_login(session, creds)
    if not ok:
        print("Login attempt failed. Aborting.")
        return 3
    print("Login successful (heuristic)")

    # Backup existing fixtures, then fetch
    backup_existing(FIXTURES_DIR, BACKUP_DIR)
    saved = fetch_pages(session, args.words, FIXTURES_DIR)
    if saved:
        print(f"Saved {len(saved)} pages to {FIXTURES_DIR}")
        # Save creds to .env and remove docs file
        save_env(creds)
        remove_docs_creds()
        return 0
    else:
        print("No pages were saved")
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
