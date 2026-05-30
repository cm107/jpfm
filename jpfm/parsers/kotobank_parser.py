"""
Kotobank parser service.

This module provides a standalone parser for extracting basic information
from Kotobank pages. It follows the same service pattern as the Jisho parser
and deliberately aims for a resilient, fixture-testable MVP: extract a
`title` and a list of `definitions` from the provided HTML.
"""

import logging
from typing import List, Optional, TypedDict

from bs4 import BeautifulSoup

from jpfm import get_logger


class ParsedKotobankEntry(TypedDict):
    """Typed dict for Kotobank parsing results."""

    title: str
    definitions: List[str]
    definitions_raw: str


class KotobankParser:
    """
    Standalone Kotobank parser.

    The parser is initialized with HTML content (from a fixture or a fetched
    page) and provides methods to extract title and definitions. It logs
    detailed warnings on missing HTML elements and errors.
    """

    def __init__(
        self,
        html_content: str,
        url: str = "memory://kotobank",
        logger: Optional[logging.Logger] = None,
    ) -> None:
        if not html_content or not isinstance(html_content, str):
            raise ValueError("html_content must be a non-empty string")

        self.url = url
        self.logger = logger or get_logger(__name__)
        self.logger.debug(f"Initializing KotobankParser for URL: {url}")

        try:
            self.soup = BeautifulSoup(html_content, "html.parser")
            self.logger.debug("Kotobank HTML parsed successfully")
        except Exception as e:
            self.logger.error(f"Failed to parse HTML: {e}", exc_info=True)
            raise

    def parse(self) -> Optional[ParsedKotobankEntry]:
        """
        Parse Kotobank page and return a structured entry.

        Returns:
            ParsedKotobankEntry or None if parsing failed or no useful data found.
        """
        try:
            title = self.extract_title()
            definitions = self.extract_definitions()
            definitions_raw = self._get_definitions_html()

            if not title and not definitions:
                self.logger.warning("No title or definitions extracted from Kotobank page")
                return None

            entry: ParsedKotobankEntry = {
                "title": title,
                "definitions": definitions,
                "definitions_raw": definitions_raw,
            }

            self.logger.info(
                f"Kotobank parse successful: title='{title}', definitions_count={len(definitions)}"
            )
            return entry

        except Exception as e:
            self.logger.error(f"Exception during Kotobank parse: {e}", exc_info=True)
            return None

    def extract_title(self) -> str:
        """
        Extracts a page title for the Kotobank entry.

        Strategy:
        1. Prefer H1 headers: `<h1>` or `<h1 class=...>`
        2. Fallback to `<title>` tag content

        Returns:
            str: Extracted title or empty string.
        """
        try:
            h1 = self.soup.find("h1")
            if h1 and h1.get_text(strip=True):
                title = h1.get_text(strip=True)
                self.logger.debug(f"Extracted title from h1: {title}")
                return title

            # Fallback to title tag
            title_tag = self.soup.find("title")
            if title_tag and title_tag.get_text(strip=True):
                title = title_tag.get_text(strip=True)
                self.logger.debug(f"Extracted title from title tag: {title}")
                return title

            self.logger.debug("No title found for Kotobank page")
            return ""

        except Exception as e:
            self.logger.error(f"Exception extracting Kotobank title: {e}", exc_info=True)
            return ""

    def extract_definitions(self) -> List[str]:
        """
        Extract definitions from Kotobank HTML.

        Strategy:
        - Try common article container selectors (article, divs with 'entry' or 'main')
        - Collect text from first N paragraphs to provide concise definitions

        Returns:
            List[str]: List of definition strings (may be empty).
        """
        try:
            candidates = []

            # Common Kotobank containers: try several selectors
            selectors = [
                "div.entryBody",  # some sites
                "div.entry-body",
                "div.article_body",
                "div.articleBody",
                "article",
                "div#main",
                "div#content",
            ]

            for sel in selectors:
                node = self.soup.select_one(sel)
                if node:
                    candidates.append(node)

            # If none found, fallback to body
            if not candidates:
                body = self.soup.body
                if body:
                    candidates.append(body)

            definitions: List[str] = []
            # Extract first few paragraphs from candidates
            for node in candidates:
                paragraphs = node.find_all("p")
                for p in paragraphs:
                    text = p.get_text(" ", strip=True)
                    if text:
                        # Normalize whitespace and skip trivial navigation text
                        if len(text) > 20:
                            definitions.append(text)
                    if len(definitions) >= 5:
                        break
                if definitions:
                    break

            if not definitions:
                # As a last resort, capture first few non-empty text blocks
                texts = [t.strip() for t in self.soup.stripped_strings if len(t.strip()) > 20]
                definitions = texts[:5]

            if definitions:
                self.logger.debug(f"Extracted {len(definitions)} definition paragraphs")
            else:
                self.logger.warning("No definition paragraphs extracted from Kotobank page")

            return definitions

        except Exception as e:
            self.logger.error(f"Exception extracting Kotobank definitions: {e}", exc_info=True)
            return []

    def _get_definitions_html(self) -> str:
        """
        Return raw HTML for the first candidate definitions container for debugging.
        """
        try:
            node = self.soup.select_one("div.entryBody, div.entry-body, div.article_body, article, div#main, div#content")
            if node:
                return str(node)
        except Exception:
            pass
        return ""
