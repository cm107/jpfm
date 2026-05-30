"""
Jisho.org parser service.

This module provides a standalone parser for extracting dictionary entries from Jisho.org.
The parser is decoupled from GUI logic and communicates via structured TypedDict objects.
"""

import logging
from typing import Dict, List, Optional, TypedDict

from bs4 import BeautifulSoup

from jpfm import get_logger


class ParsedJishoEntry(TypedDict):
    """
    Typed dictionary representing a parsed Jisho dictionary entry.

    Attributes:
        reading: The reading (furigana/hiragana) of the word.
        kanji: The kanji (written form) of the word.
        definitions: List of definitions grouped by part of speech.
        definitions_raw: Raw HTML definitions for debugging.
    """

    reading: str
    kanji: str
    definitions: List[str]
    definitions_raw: str


class JishoParser:
    """
    Standalone Jisho.org dictionary parser.

    This parser extracts dictionary entries from Jisho.org HTML and returns
    structured data without any GUI dependencies. It integrates logging to
    track extraction state and catch parsing failures.

    Attributes:
        soup (BeautifulSoup): Parsed HTML document.
        url (str): Source URL (for logging/debugging).
        logger (logging.Logger): Logger instance for this parser.
    """

    def __init__(
        self,
        html_content: str,
        url: str = "memory://jisho",
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Initialize the Jisho parser with HTML content.

        Args:
            html_content: Raw HTML string from Jisho.org (or local fixture).
            url: Source URL for logging purposes (default: "memory://jisho").
            logger: Optional logger instance. If None, creates a new one.

        Raises:
            ValueError: If html_content is empty or invalid.
        """
        if not html_content or not isinstance(html_content, str):
            raise ValueError("html_content must be a non-empty string")

        self.url = url
        self.logger = logger or get_logger(__name__)
        self.logger.debug(f"Initializing JishoParser for URL: {url}")

        try:
            self.soup = BeautifulSoup(html_content, "html.parser")
            self.logger.debug("HTML parsed successfully")
        except Exception as e:
            self.logger.error(f"Failed to parse HTML: {e}", exc_info=True)
            raise

    def parse(self, word: Optional[str] = None) -> Optional[ParsedJishoEntry]:
        """
        Parse a Jisho dictionary entry.

        This is the main entry point for parsing. It attempts to extract all
        available information from the HTML and returns a structured dictionary.

        Args:
            word: Optional word being queried (used for logging).

        Returns:
            ParsedJishoEntry: Parsed entry with reading, kanji, and definitions.
            None: If no valid entry is found in the HTML.
        """
        self.logger.debug(f"Starting parse for word: {word}")

        try:
            # Check if any results exist
            if self._has_no_results():
                self.logger.warning(f"No results found for word: {word}")
                return None

            reading = self.extract_reading()
            kanji = self.extract_kanji()
            definitions = self.extract_definitions()
            definitions_raw = self._get_definitions_html()

            if not reading and not kanji:
                self.logger.error(
                    "Failed to extract both reading and kanji from entry"
                )
                return None

            entry: ParsedJishoEntry = {
                "reading": reading,
                "kanji": kanji,
                "definitions": definitions,
                "definitions_raw": definitions_raw,
            }

            self.logger.info(
                f"Successfully parsed entry: kanji='{kanji}', reading='{reading}', "
                f"definitions_count={len(definitions)}"
            )
            return entry

        except Exception as e:
            self.logger.error(f"Exception during parse: {e}", exc_info=True)
            return None

    def extract_reading(self) -> str:
        """
        Extract the reading (furigana/hiragana) from the entry.

        This method attempts to extract the reading using CSS selectors
        that target the furigana span elements in the entry.

        Returns:
            str: The extracted reading, or empty string if not found.
        """
        try:
            # Find the main entry container
            entry_container = self.soup.find("div", class_="concept_light clearfix")
            if not entry_container:
                self.logger.warning("Entry container not found: div.concept_light.clearfix")
                return ""

            # Try to find furigana/reading
            # Jisho structure: span.furigana with nested span.kanji-*-up for furigana chars
            furigana_span = entry_container.find("span", class_="furigana")
            if furigana_span:
                # Extract all text content from furigana span (includes small kanji-up spans)
                reading_parts = []
                for element in furigana_span.children:
                    if isinstance(element, str):
                        reading_parts.append(element.strip())
                    elif element.name == "span" and "kanji" in element.get("class", []):
                        reading_parts.append(element.get_text(strip=True))
                
                reading = "".join(reading_parts).strip()
                if reading:
                    self.logger.debug(f"Extracted reading: '{reading}'")
                    return reading

            self.logger.debug("Reading not found using furigana selector")
            return ""

        except Exception as e:
            self.logger.error(f"Exception extracting reading: {e}", exc_info=True)
            return ""

    def extract_kanji(self) -> str:
        """
        Extract the kanji (written form) from the entry.

        This method attempts to extract the kanji/writing using CSS selectors
        that target the text span elements in the entry.

        Returns:
            str: The extracted kanji, or empty string if not found.
        """
        try:
            # Find the main entry container
            entry_container = self.soup.find("div", class_="concept_light clearfix")
            if not entry_container:
                self.logger.warning("Entry container not found: div.concept_light.clearfix")
                return ""

            # Jisho structure: span.text contains the written form (kanji or hiragana)
            text_span = entry_container.find("span", class_="text")
            if text_span:
                kanji = text_span.get_text(strip=True)
                if kanji:
                    self.logger.debug(f"Extracted kanji: '{kanji}'")
                    return kanji

            self.logger.debug("Kanji not found using text selector")
            return ""

        except Exception as e:
            self.logger.error(f"Exception extracting kanji: {e}", exc_info=True)
            return ""

    def extract_definitions(self) -> List[str]:
        """
        Extract definitions from the entry.

        This method extracts definitions grouped by part of speech. Each definition
        is a plain text string without HTML markup.

        Returns:
            List[str]: List of definition strings (each representing a meaning).
                Returns empty list if no definitions found.
        """
        try:
            definitions = []

            # Find the main entry container
            entry_container = self.soup.find("div", class_="concept_light clearfix")
            if not entry_container:
                self.logger.warning("Entry container not found: div.concept_light.clearfix")
                return definitions

            # Find the meanings wrapper
            meanings_wrapper = entry_container.find(
                "div", class_="concept_light-meanings"
            )
            if not meanings_wrapper:
                self.logger.debug("Meanings wrapper not found: div.concept_light-meanings")
                return definitions

            # Extract all meaning blocks (each represents a definition)
            meaning_definitions = meanings_wrapper.find_all("div", class_="meaning-definition")
            
            if not meaning_definitions:
                self.logger.debug("No meaning definitions found")
                return definitions

            for i, meaning_def in enumerate(meaning_definitions):
                try:
                    # Find the actual definition text
                    meaning_text_span = meaning_def.find("span", class_="meaning-meaning")
                    if meaning_text_span:
                        definition = meaning_text_span.get_text(strip=True)
                        if definition:
                            definitions.append(definition)
                            self.logger.debug(f"Extracted definition {i + 1}: '{definition[:50]}...'")
                except Exception as e:
                    self.logger.warning(
                        f"Error extracting definition {i + 1}: {e}", exc_info=False
                    )
                    continue

            if definitions:
                self.logger.debug(f"Extracted {len(definitions)} definitions total")
            else:
                self.logger.warning("No definitions were successfully extracted")

            return definitions

        except Exception as e:
            self.logger.error(f"Exception extracting definitions: {e}", exc_info=True)
            return []

    def _has_no_results(self) -> bool:
        """
        Check if the HTML indicates no results were found.

        Returns:
            bool: True if the page indicates no results, False otherwise.
        """
        no_results_div = self.soup.find("div", id="no-matches")
        return no_results_div is not None

    def _get_definitions_html(self) -> str:
        """
        Get raw HTML of the definitions section for debugging.

        Returns:
            str: Raw HTML string of the meanings wrapper, or empty string if not found.
        """
        try:
            entry_container = self.soup.find("div", class_="concept_light clearfix")
            if entry_container:
                meanings_wrapper = entry_container.find(
                    "div", class_="concept_light-meanings"
                )
                if meanings_wrapper:
                    return str(meanings_wrapper)
        except Exception as e:
            self.logger.debug(f"Error getting definitions HTML: {e}", exc_info=False)
        
        return ""
