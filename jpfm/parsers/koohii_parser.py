"""
Koohii parser service.

Simplified MVP: extracts `kanji` and `mnemonic` text blocks from a Koohii HTML fixture.
"""

import logging
from typing import List, Optional, TypedDict

from bs4 import BeautifulSoup

from jpfm import get_logger


class ParsedKoohiiEntry(TypedDict):
    kanji: str
    mnemonic: str
    mnemonic_raw: str


class KoohiiParser:
    """
    Simple Koohii parser for extracting kanji mnemonics.

    The real site has complex interactions; this MVP uses straightforward
    selectors and is tested against local fixtures.
    """

    def __init__(self, html_content: str, url: str = "memory://koohii", logger: Optional[logging.Logger] = None) -> None:
        if not html_content or not isinstance(html_content, str):
            raise ValueError("html_content must be a non-empty string")

        self.url = url
        self.logger = logger or get_logger(__name__)
        self.logger.debug(f"Initializing KoohiiParser for URL: {url}")

        try:
            self.soup = BeautifulSoup(html_content, "html.parser")
            self.logger.debug("Koohii HTML parsed successfully")
        except Exception as e:
            self.logger.error(f"Failed to parse HTML: {e}", exc_info=True)
            raise

    def parse(self) -> Optional[ParsedKoohiiEntry]:
        try:
            kanji = self.extract_kanji()
            mnemonic = self.extract_mnemonic()
            mnemonic_raw = self._get_mnemonic_html()

            if not kanji and not mnemonic:
                self.logger.warning("No kanji or mnemonic extracted from Koohii page")
                return None

            entry: ParsedKoohiiEntry = {
                "kanji": kanji,
                "mnemonic": mnemonic,
                "mnemonic_raw": mnemonic_raw,
            }
            self.logger.info(f"Koohii parse successful: kanji='{kanji}'")
            return entry
        except Exception as e:
            self.logger.error(f"Exception during Koohii parse: {e}", exc_info=True)
            return None

    def extract_kanji(self) -> str:
        try:
            # Preferred selector: h1. Fallback to .kanji or title
            h1 = self.soup.find("h1")
            if h1 and h1.get_text(strip=True):
                val = h1.get_text(strip=True)
                self.logger.debug(f"Extracted kanji from h1: {val}")
                return val

            kanji_node = self.soup.select_one(".kanji")
            if kanji_node and kanji_node.get_text(strip=True):
                val = kanji_node.get_text(strip=True)
                self.logger.debug(f"Extracted kanji from .kanji: {val}")
                return val

            title = self.soup.title
            if title and title.get_text(strip=True):
                val = title.get_text(strip=True)
                self.logger.debug(f"Extracted kanji from title: {val}")
                return val

            self.logger.debug("No kanji found in Koohii page")
            return ""
        except Exception as e:
            self.logger.error(f"Exception extracting kanji: {e}", exc_info=True)
            return ""

    def extract_mnemonic(self) -> str:
        try:
            # Koohii fixtures will provide .mnemonic class or div#mnemonic
            node = self.soup.select_one(".mnemonic, #mnemonic, div.mnemonic-text")
            if node:
                text = node.get_text(" ", strip=True)
                self.logger.debug(f"Extracted mnemonic length={len(text)}")
                return text

            # Fallback: take first paragraph
            p = self.soup.find("p")
            if p and p.get_text(strip=True):
                return p.get_text(strip=True)

            return ""
        except Exception as e:
            self.logger.error(f"Exception extracting mnemonic: {e}", exc_info=True)
            return ""

    def _get_mnemonic_html(self) -> str:
        try:
            node = self.soup.select_one(".mnemonic, #mnemonic, div.mnemonic-text")
            if node:
                return str(node)
        except Exception:
            pass
        return ""
