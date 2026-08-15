"""
Jisho.org parser service.

This module provides a standalone parser for extracting dictionary entries from Jisho.org.
The parser is decoupled from GUI logic and communicates via structured TypedDict objects.
"""

import logging
import unicodedata
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
                    f"Failed to extract both reading and kanji from entry (search_word={word})"
                )
                return None

            entry: ParsedJishoEntry = {
                "reading": reading,
                "kanji": kanji,
                "definitions": definitions,
                "definitions_raw": definitions_raw,
            }

            self.logger.info(
                f"Successfully parsed entry: search_word={word}, kanji='{kanji}', reading='{reading}', "
                f"definitions_count={len(definitions)}"
            )
            return entry

        except Exception as e:
            self.logger.error(f"Exception during parse: {e}", exc_info=True)
            return None

    @staticmethod
    def _is_kana_char(char: str) -> bool:
        """Return True when the character is hiragana or katakana."""
        if not char:
            return False
        if char in {"ー", "〜"}:
            return True
        name = unicodedata.name(char, "")
        return "HIRAGANA" in name or "KATAKANA" in name

    @staticmethod
    def _normalized_text(value: str) -> str:
        return value.replace("\n", "").replace(" ", "")

    @staticmethod
    def _collect_nonempty_text(tags: List) -> List[str]:
        values: List[str] = []
        for tag in tags:
            text = tag.get_text(separator="", strip=True)
            if text:
                values.append(text)
        return values

    def extract_reading(self) -> str:
        """
        Extract the full reading for the entry, including okurigana.

        Jisho often splits the reading into a furigana root and a kana suffix
        (`okurigana`) across separate spans. When that happens, we need to
        combine the root with the remaining kana text to get the full word
        reading rather than only the kanji reading.

        Returns:
            str: The extracted reading, or empty string if not found.
        """
        try:
            entry_container = self.soup.find("div", class_="concept_light clearfix")
            if not entry_container:
                self.logger.warning("Entry container not found: div.concept_light.clearfix")
                return ""

            furigana_span = entry_container.find("span", class_="furigana")
            text_span = entry_container.find("span", class_="text")

            furigana_parts = []
            if furigana_span:
                ruby_rt = furigana_span.find("rt")
                if ruby_rt and ruby_rt.get_text(strip=True):
                    rt_text = ruby_rt.get_text(strip=True)
                    ruby_base = furigana_span.find("rb")
                    if ruby_base and len(ruby_base.get_text(strip=True)) == len(rt_text):
                        furigana_parts = list(rt_text)
                    else:
                        furigana_parts = [rt_text]
                    if furigana_span.find_all("rt") and len(furigana_span.find_all("rt")) > 1:
                        furigana_parts = [tag.get_text(strip=True) for tag in furigana_span.find_all("rt") if tag.get_text(strip=True)]
                else:
                    furigana_parts = self._collect_nonempty_text(furigana_span.find_all("span"))
                    if not furigana_parts:
                        collected = furigana_span.get_text(separator="", strip=True)
                        if collected:
                            furigana_parts = [collected]

            if text_span:
                text_value = self._normalized_text(text_span.get_text(separator="", strip=True))
                child_spans = text_span.find_all("span")
                if not child_spans and furigana_parts:
                    direct_reading = "".join(furigana_parts)
                    if direct_reading:
                        self.logger.debug(f"Extracted full reading from plain furigana: '{direct_reading}'")
                        return direct_reading

                okurigana_chars = []
                for span in child_spans:
                    span_text = self._normalized_text(span.get_text(separator="", strip=True))
                    if span_text:
                        okurigana_chars.extend(list(span_text))

                furigana_queue = list(furigana_parts)
                reading = ""

                for char in text_value:
                    if okurigana_chars and char == okurigana_chars[0]:
                        reading += okurigana_chars.pop(0)
                        continue

                    if self._is_kana_char(char):
                        reading += char
                        continue

                    if furigana_queue:
                        reading += furigana_queue.pop(0)
                        continue

                        # If we reach here, the character is not kana and there
                        # is no furigana available to map to it. Do not include
                        # the original kanji character in the reading output;
                        # this preserves proper kana-only readings (okurigana
                        # and distributed furigana). Skip the written-form
                        # character instead of copying it into the reading.
                        continue

                if reading:
                    self.logger.debug(f"Extracted full reading: '{reading}'")
                    return reading

            if furigana_parts:
                furigana_text = "".join(furigana_parts)
                self.logger.debug(f"Extracted furigana-only reading: '{furigana_text}'")
                return furigana_text

            if text_span:
                reading_candidate = text_span.get_text(separator="", strip=True)
                if reading_candidate:
                    self.logger.debug(f"Fallback reading from text span: '{reading_candidate}'")
                    return reading_candidate

            self.logger.debug("Reading not found using furigana or text selectors")
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
