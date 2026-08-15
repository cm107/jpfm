"""
Dictionary manager service for cache-aware word lookups.

This service orchestrates the parsing pipeline, implementing a cache-first
pattern to minimize redundant web requests. It coordinates with the storage
layer and delegates to source-specific parsers.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup

from jpfm import get_logger
from jpfm.storage import StorageService
from jpfm.parsers.jisho_parser import JishoParser
from jpfm.parsers.kotobank_parser import KotobankParser
from jpfm.parsers.koohii_parser import KoohiiParser


class ParserFactory(ABC):
    """Base factory for creating parsers."""

    @abstractmethod
    def create_parser(self, html_content: str, url: str):
        """Create a parser instance with HTML content."""
        pass

    @abstractmethod
    def get_url(self, word: str) -> str:
        """Get the URL to fetch for a given word."""
        pass

    @abstractmethod
    def fetch_html(self, word: str) -> Optional[str]:
        """Fetch HTML for a given word."""
        pass


class JishoParserFactory(ParserFactory):
    """Factory for Jisho parser."""

    def get_url(self, word: str) -> str:
        return f"https://jisho.org/search/{word}"

    def fetch_html(self, word: str) -> Optional[str]:
        try:
            response = requests.get(self.get_url(word), timeout=10)
            response.raise_for_status()
            return response.text
        except Exception:
            return None

    def create_parser(self, html_content: str, url: str):
        return JishoParser(html_content=html_content, url=url)


class KotobankParserFactory(ParserFactory):
    """Factory for Kotobank parser."""

    def get_url(self, word: str) -> str:
        return f"https://kotobank.jp/word/{word}"

    def fetch_html(self, word: str) -> Optional[str]:
        try:
            response = requests.get(self.get_url(word), timeout=10)
            response.raise_for_status()
            return response.text
        except Exception:
            return None

    def create_parser(self, html_content: str, url: str):
        return KotobankParser(html_content=html_content, url=url)


class KoohiiParserFactory(ParserFactory):
    """Factory for Koohii parser."""

    def get_url(self, word: str) -> str:
        return f"https://kanji.koohii.com/kanji/{word}"

    def fetch_html(self, word: str) -> Optional[str]:
        try:
            response = requests.get(self.get_url(word), timeout=10)
            response.raise_for_status()
            return response.text
        except Exception:
            return None

    def create_parser(self, html_content: str, url: str):
        return KoohiiParser(html_content=html_content, url=url)


class DictionaryManager:
    """
    Orchestrator for dictionary lookups with intelligent caching.

    The manager implements a cache-first pattern:
    1. Check if entry exists in storage for the given source.
    2. If cached, load and return immediately (cache hit).
    3. If not cached, fetch HTML and call the appropriate parser (cache miss).
    4. On successful parse, save to storage before returning.

    Attributes:
        storage (StorageService): Cache layer for parsed entries.
        factories (dict): Mapping of source names to parser factories.
        logger (logging.Logger): Logger instance for diagnostics.
    """

    # Supported parsers and their sources
    SUPPORTED_SOURCES = ["jisho", "kotobank", "koohii"]

    def __init__(
        self,
        storage: Optional[StorageService] = None,
        base_dir: str = "storage",
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Initialize the DictionaryManager.

        Args:
            storage (StorageService, optional): Cache layer. If None, creates a new one.
            base_dir (str): Base directory for storage. Defaults to `storage/`.
            logger (logging.Logger, optional): Logger instance. If None, creates a new one.

        Raises:
            ValueError: If storage or base_dir are invalid.
        """
        self.storage = storage or StorageService(base_dir=base_dir, logger=logger)
        self.logger = logger or get_logger(__name__)

        # Initialize parser factories
        self.factories = {
            "jisho": JishoParserFactory(),
            "kotobank": KotobankParserFactory(),
            "koohii": KoohiiParserFactory(),
        }

        self.logger.info(
            f"DictionaryManager initialized with sources: {self.SUPPORTED_SOURCES}"
        )

    def _validate_source(self, source: str) -> None:
        """
        Validate that the requested source is supported.

        Args:
            source (str): Parser source to validate.

        Raises:
            ValueError: If source is not supported.
        """
        if source not in self.SUPPORTED_SOURCES:
            raise ValueError(
                f"Unsupported source: {source}. Must be one of {self.SUPPORTED_SOURCES}"
            )

    def get_entry(self, source: str, word: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a dictionary entry with cache-aware lookup.

        Implements the cache-first pattern:
        1. Check storage for existing entry (cache hit).
        2. If not cached, fetch HTML and parse from web (cache miss) and save.

        Args:
            source (str): Parser source ('jisho', 'kotobank', or 'koohii').
            word (str): Search term (e.g., '愛').

        Returns:
            dict or None: Dictionary entry with parsed data, or None if parsing fails.

        Raises:
            ValueError: If source is not supported or word is empty.
        """
        if not word or not isinstance(word, str):
            raise ValueError("word must be a non-empty string")

        self._validate_source(source)

        # Check cache first
        cached_entry = self.storage.load(source, word)
        if cached_entry is not None:
            self.logger.info(f"Cache hit: {source}/{word}")
            return cached_entry

        # Cache miss: fetch and parse from web
        self.logger.info(f"Cache miss: {source}/{word}, fetching and parsing...")
        try:
            factory = self.factories[source]
            url = factory.get_url(word)

            # Fetch HTML
            html_content = factory.fetch_html(word)
            if not html_content:
                self.logger.warning(f"Failed to fetch HTML for {source}/{word}")
                return None

            # Create parser and parse
            parser = factory.create_parser(html_content, url)
            parsed_entry = parser.parse(word)

            if parsed_entry is None:
                self.logger.warning(f"Parser returned None for {source}/{word}")
                return None

            # Save to cache before returning
            if self.storage.save(source, word, parsed_entry):
                self.logger.info(f"Saved to cache: {source}/{word}")
            else:
                self.logger.warning(f"Failed to cache: {source}/{word}")

            return parsed_entry
        except Exception as e:
            self.logger.error(
                f"Error parsing {source}/{word}: {e}",
                exc_info=True,
            )
            return None

    def batch_get_entries(
        self,
        source: str,
        words: List[str],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve multiple dictionary entries efficiently.

        Performs cache-aware lookups for each word, logging cache hit/miss statistics.

        Args:
            source (str): Parser source ('jisho', 'kotobank', or 'koohii').
            words (list): List of search terms to look up.

        Returns:
            list: List of parsed entries (None values for failed lookups are filtered out).

        Raises:
            ValueError: If source is not supported or words is empty.
        """
        if not words or not isinstance(words, list):
            raise ValueError("words must be a non-empty list")

        self._validate_source(source)

        entries = []
        cache_hits = 0
        cache_misses = 0

        total = len(words)
        for idx, word in enumerate(words):
            # Respect cancellation requests
            try:
                if cancel_check and cancel_check():
                    self.logger.info("Batch parsing cancelled by request")
                    break
            except Exception:
                # Ignore cancel_check errors and continue
                self.logger.debug("cancel_check callable raised an exception", exc_info=True)
            # Report progress before processing the word
            try:
                if progress_callback:
                    progress_callback(idx + 1, total, word)
            except Exception:
                # Don't let callback errors stop processing
                self.logger.debug("Progress callback raised an exception", exc_info=True)

            entry = self.get_entry(source, word)
            if entry is not None:
                entries.append(entry)

        self.logger.info(
            f"Batch lookup for {source}: {len(entries)} entries retrieved"
        )
        return entries

    def clear_cache(self, source: Optional[str] = None) -> bool:
        """
        Clear cached entries.

        If `source` is specified, only entries for that source are cleared.
        Otherwise, all cache entries are cleared.

        Args:
            source (str, optional): Parser source to clear. If None, clears all cache.

        Returns:
            bool: True if clear was successful, False otherwise.

        Raises:
            ValueError: If source is provided and is not supported.
        """
        if source is not None:
            self._validate_source(source)

        result = self.storage.clear_cache(source)
        if result:
            target = source or "all sources"
            self.logger.info(f"Cleared cache for {target}")
        else:
            self.logger.error("Failed to clear cache")

        return result

    def list_cached_words(self, source: str) -> List[str]:
        """
        List all cached words for a given source.

        Args:
            source (str): Parser source ('jisho', 'kotobank', or 'koohii').

        Returns:
            list: Sorted list of cached word strings.

        Raises:
            ValueError: If source is not supported.
        """
        self._validate_source(source)
        words = self.storage.list_cached_words(source)
        self.logger.debug(f"Listed {len(words)} cached words for {source}")
        return words

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get statistics about cached entries across all sources.

        Returns:
            dict: Mapping of source names to cached word counts.
        """
        stats = {}
        for source in self.SUPPORTED_SOURCES:
            count = len(self.storage.list_cached_words(source))
            stats[source] = count

        total = sum(stats.values())
        self.logger.debug(f"Cache stats: {total} total entries across sources")
        return stats
