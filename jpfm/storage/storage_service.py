"""
Storage service for caching parsed dictionary entries.

This module provides a robust caching layer that persists parsed dictionary
entries to disk, preventing redundant web requests and improving performance.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any

from jpfm import get_logger

# Current schema version for cache entries
CURRENT_SCHEMA_VERSION = "1.0"
# Recognize older cache entries that can still be migrated to the current schema.
LEGACY_SCHEMA_VERSIONS = ["0.5"]


def _version_to_tuple(version: str) -> tuple:
    """Convert a schema version string into a comparable tuple."""
    try:
        return tuple(int(part) for part in version.split(".") if part.isdigit())
    except Exception:
        return ()


def _is_legacy_schema_version(version: Optional[str]) -> bool:
    """Return True if a cached schema version is older than the current schema."""
    if version is None:
        return True

    try:
        return _version_to_tuple(version) < _version_to_tuple(CURRENT_SCHEMA_VERSION)
    except Exception:
        return False


class StorageService:
    """
    Service for persisting and retrieving cached dictionary entries.

    The storage layer maintains parsed entries in `storage/cache/{source}/{word}.json`,
    with metadata for versioning and cache invalidation. Each entry includes:
    - `_version`: Schema version for compatibility checking.
    - `_source`: Source parser (jisho, kotobank, koohii).
    - `_cached_at`: ISO timestamp when the entry was cached.

    Attributes:
        base_dir (Path): Root directory for cache storage (default: `storage/`).
        cache_dir (Path): Computed cache directory (`storage/cache/`).
        logger (logging.Logger): Logger instance for diagnostics.
    """

    def __init__(
        self,
        base_dir: str = "storage",
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Initialize the StorageService.

        Args:
            base_dir (str): Root directory for cache storage. Defaults to `storage/`.
            logger (logging.Logger, optional): Logger instance. If None, creates a new one.

        Raises:
            ValueError: If base_dir is empty or None.
        """
        if not base_dir or not isinstance(base_dir, str):
            raise ValueError("base_dir must be a non-empty string")

        self.base_dir = Path(base_dir)
        self.cache_dir = self.base_dir / "cache"
        self.logger = logger or get_logger(__name__)

        self.logger.debug(f"Initializing StorageService with base_dir={self.base_dir}")
        self._ensure_cache_directory()

    def _ensure_cache_directory(self) -> None:
        """
        Ensure the cache directory exists, creating it if necessary.

        This method is called during initialization to prepare the cache structure.
        """
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Cache directory ready: {self.cache_dir}")
        except Exception as e:
            self.logger.error(f"Failed to create cache directory: {e}", exc_info=True)
            raise

    def _get_entry_path(self, source: str, word: str) -> Path:
        """
        Compute the file path for a cached entry.

        Args:
            source (str): Parser source (e.g., 'jisho', 'kotobank', 'koohii').
            word (str): Search term (e.g., '愛').

        Returns:
            Path: Full path to the cache file.

        Raises:
            ValueError: If source or word are empty.
        """
        if not source or not isinstance(source, str):
            raise ValueError("source must be a non-empty string")
        if not word or not isinstance(word, str):
            raise ValueError("word must be a non-empty string")

        source_dir = self.cache_dir / source
        return source_dir / f"{word}.json"

    def save(self, source: str, word: str, parsed_data: Dict[str, Any]) -> bool:
        """
        Save a parsed dictionary entry to cache.

        The entry is stored with metadata including versioning and cache timestamp.
        If the entry already exists, it is overwritten.

        Args:
            source (str): Parser source (e.g., 'jisho', 'kotobank', 'koohii').
            word (str): Search term (e.g., '愛').
            parsed_data (dict): Parsed entry data to cache.

        Returns:
            bool: True if save was successful, False otherwise.

        Raises:
            ValueError: If source, word, or parsed_data are invalid.
        """
        if not parsed_data or not isinstance(parsed_data, dict):
            raise ValueError("parsed_data must be a non-empty dictionary")

        try:
            entry_path = self._get_entry_path(source, word)
            entry_path.parent.mkdir(parents=True, exist_ok=True)

            # Add metadata
            entry_with_metadata = {
                "_version": CURRENT_SCHEMA_VERSION,
                "_source": source,
                "_cached_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                **parsed_data,
            }

            with open(entry_path, "w", encoding="utf-8") as f:
                json.dump(entry_with_metadata, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Cached entry: {source}/{word} at {entry_path}")
            return True
        except Exception as e:
            self.logger.error(
                f"Failed to save cache entry for {source}/{word}: {e}",
                exc_info=True,
            )
            return False

    def load(self, source: str, word: str) -> Optional[Dict[str, Any]]:
        """
        Load a cached dictionary entry from disk.

        Performs version validation: if the cached version does not match
        `CURRENT_SCHEMA_VERSION`, the entry is considered stale and None is returned.

        Args:
            source (str): Parser source (e.g., 'jisho', 'kotobank', 'koohii').
            word (str): Search term (e.g., '愛').

        Returns:
            dict or None: Cached entry (minus metadata fields), or None if not found or stale.
        """
        try:
            entry_path = self._get_entry_path(source, word)

            if not entry_path.exists():
                self.logger.debug(f"Cache miss: {source}/{word} not found")
                return None

            with open(entry_path, "r", encoding="utf-8") as f:
                cached_entry = json.load(f)

            # Validate version
            cached_version = cached_entry.get("_version")
            if cached_version != CURRENT_SCHEMA_VERSION:
                if _is_legacy_schema_version(cached_version):
                    migrated_entry = self._migrate_entry(cached_entry, source)
                    if migrated_entry is None:
                        self.logger.warning(
                            f"Legacy cache entry {source}/{word} could not be migrated from version {cached_version}"
                        )
                        return None

                    with open(entry_path, "w", encoding="utf-8") as f:
                        json.dump(migrated_entry, f, ensure_ascii=False, indent=2)

                    cached_entry = migrated_entry
                    self.logger.info(
                        f"Migrated cache entry {source}/{word} from {cached_version or 'unknown'} to {CURRENT_SCHEMA_VERSION}"
                    )
                else:
                    self.logger.warning(
                        f"Cache entry {source}/{word} has stale version {cached_version}; "
                        f"expected {CURRENT_SCHEMA_VERSION}"
                    )
                    return None

            # Remove metadata before returning
            entry_data = {
                k: v
                for k, v in cached_entry.items()
                if not k.startswith("_")
            }

            self.logger.debug(f"Cache hit: {source}/{word}")
            return entry_data
        except Exception as e:
            self.logger.error(
                f"Failed to load cache entry for {source}/{word}: {e}",
                exc_info=True,
            )
            return None

    def exists(self, source: str, word: str) -> bool:
        """
        Check if a valid cached entry exists.

        An entry is valid if:
        1. The file exists on disk.
        2. The cached version matches or can be migrated to `CURRENT_SCHEMA_VERSION`.

        Args:
            source (str): Parser source (e.g., 'jisho', 'kotobank', 'koohii').
            word (str): Search term (e.g., '愛').

        Returns:
            bool: True if a valid cached entry exists, False otherwise.
        """
        try:
            entry_path = self._get_entry_path(source, word)

            if not entry_path.exists():
                return False

            with open(entry_path, "r", encoding="utf-8") as f:
                cached_entry = json.load(f)

            cached_version = cached_entry.get("_version")
            is_valid = (
                cached_version == CURRENT_SCHEMA_VERSION
                or _is_legacy_schema_version(cached_version)
            )

            if not is_valid:
                self.logger.debug(f"Stale cache entry for {source}/{word}")

            return is_valid
        except Exception as e:
            self.logger.error(
                f"Error checking cache existence for {source}/{word}: {e}",
                exc_info=True,
            )
            return False

    def list_cached_words(self, source: str) -> List[str]:
        """
        List all cached words for a given source.

        Only valid entries (matching current schema version) are returned.

        Args:
            source (str): Parser source (e.g., 'jisho', 'kotobank', 'koohii').

        Returns:
            list: List of cached word strings (filenames without .json extension).
        """
        try:
            source_dir = self.cache_dir / source

            if not source_dir.exists():
                self.logger.debug(f"No cache directory for source: {source}")
                return []

            cached_words = []
            for json_file in source_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        entry = json.load(f)
                    cached_version = entry.get("_version")
                    if (
                        cached_version == CURRENT_SCHEMA_VERSION
                        or _is_legacy_schema_version(cached_version)
                    ):
                        cached_words.append(json_file.stem)
                except Exception:
                    # Skip malformed entries
                    pass

            self.logger.info(f"Listed {len(cached_words)} cached words for {source}")
            return sorted(cached_words)
        except Exception as e:
            self.logger.error(
                f"Failed to list cached words for {source}: {e}",
                exc_info=True,
            )
            return []

    def _migrate_entry(
        self, cached_entry: Dict[str, Any], source: str
    ) -> Optional[Dict[str, Any]]:
        """
        Migrate a cache entry from an older schema version to the current schema.

        Args:
            cached_entry (dict): Raw entry loaded from disk.
            source (str): Expected parser source for the entry.

        Returns:
            dict or None: Migrated entry with current schema metadata, or None if migration fails.
        """
        current_version = cached_entry.get("_version")

        if current_version == CURRENT_SCHEMA_VERSION:
            return cached_entry

        if not _is_legacy_schema_version(current_version):
            return None

        migrated_entry = {
            **cached_entry,
            "_version": CURRENT_SCHEMA_VERSION,
            "_source": cached_entry.get("_source", source),
            "_cached_at": cached_entry.get(
                "_cached_at",
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            ),
        }

        return migrated_entry

    def clear_cache(self, source: Optional[str] = None) -> bool:
        """
        Clear cache entries.

        If `source` is specified, only entries for that source are cleared (only .json files).
        Otherwise, all cache entries are cleared (only .json files in all source dirs).

        This intentionally preserves other files such as .gitignore and .gitkeep.

        Args:
            source (str, optional): Parser source to clear. If None, clears all cache.

        Returns:
            bool: True if clear was successful, False otherwise.
        """
        try:
            if source:
                # Clear a specific source directory's JSON files only
                source_dir = self.cache_dir / source
                if source_dir.exists():
                    removed = 0
                    for json_file in source_dir.glob("*.json"):
                        try:
                            json_file.unlink()
                            removed += 1
                        except Exception:
                            pass
                    self.logger.info(f"Cleared {removed} cached json files for source: {source}")
            else:
                # Clear all .json files from every source directory
                removed_total = 0
                if self.cache_dir.exists():
                    for child in self.cache_dir.iterdir():
                        if child.is_dir():
                            for json_file in child.glob("*.json"):
                                try:
                                    json_file.unlink()
                                    removed_total += 1
                                except Exception:
                                    pass
                self.logger.info(f"Cleared {removed_total} cached json files across all sources")

            return True
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}", exc_info=True)
            return False
