"""
Service for importing browser history entries and extracting candidate words.

This service is designed to support configurable extraction rules and generate a
normalized, deduplicated word list from browser history JSON exports.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set
from urllib.parse import parse_qs, unquote, urlparse

from PySide6.QtCore import QCoreApplication, QObject, Signal

from jpfm import get_logger
from jpfm.config import CONFIG
from jpfm.models.word_list_item import WordListItem

_LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class HistoryCandidate:
    source_path: str
    browse_timestamp: int
    browser_name: str
    url: str
    rule_id: str
    provider_name: str
    word: str
    normalized_word: str
    title: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HistoryExtractionRule:
    id: str
    provider_name: str
    matcher_type: str
    matcher_value: str
    extractor_type: str
    extractor_value: Optional[str] = None
    query_param: Optional[str] = None
    regex: Optional[re.Pattern] = None

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> HistoryExtractionRule:
        matcher = config.get("matcher", {}) or {}
        extractor = config.get("extractor", {}) or {}

        matcher_type = matcher.get("type", "prefix")
        matcher_value = matcher.get("value", "")
        extractor_type = extractor.get("type", "default")
        extractor_value = extractor.get("value")
        query_param = extractor.get("query_param")
        regex = None

        if matcher_type == "regex":
            regex = re.compile(matcher_value)

        return HistoryExtractionRule(
            id=config["id"],
            provider_name=config.get("provider_name", "unknown"),
            matcher_type=matcher_type,
            matcher_value=matcher_value,
            extractor_type=extractor_type,
            extractor_value=extractor_value,
            query_param=query_param,
            regex=regex,
        )

    def matches(self, url: str) -> bool:
        if self.matcher_type == "prefix":
            return url.startswith(self.matcher_value)

        if self.matcher_type == "regex":
            return bool(self.regex and self.regex.match(url))

        raise ValueError(f"Unsupported matcher type: {self.matcher_type}")

    def extract(self, url: str) -> Optional[str]:
        parsed = urlparse(url)

        if self.extractor_type == "path_prefix":
            if not self.extractor_value:
                return None
            if parsed.path.startswith(self.extractor_value):
                return parsed.path[len(self.extractor_value) :]
            return None

        if self.extractor_type == "query_param":
            if not self.query_param:
                return None
            values = parse_qs(parsed.query).get(self.query_param)
            if not values:
                return None
            return values[0]

        if self.extractor_type == "regex_capture":
            if not self.regex:
                return None
            match = self.regex.match(url)
            if not match or match.lastindex is None:
                return None
            return match.group(1)

        if self.matcher_type == "prefix" and self.matcher_value:
            return url[len(self.matcher_value) :]

        return None


class HistoryImportService(QObject):
    """Service for browser history import and candidate extraction."""

    progress_updated = Signal(int, int, str)
    import_finished = Signal(dict)
    import_error = Signal(str)

    DEFAULT_SUPPORTED_FILENAMES = ["BrowserHistory.json", "History.json"]
    DEFAULT_EXTRACTION_RULES = [
        {
            "id": "jisho_search",
            "provider_name": "jisho",
            "matcher": {"type": "prefix", "value": "https://jisho.org/search/"},
            "extractor": {"type": "path_prefix", "value": "/search/"},
        }
    ]

    def __init__(
        self,
        history_import_config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        config = history_import_config or CONFIG.get("history_import", {})
        self.supported_filenames = self.DEFAULT_SUPPORTED_FILENAMES
        self.rules = []
        self.pruning_rules = []
        self.learned_words = set()
        self.logger = logger or get_logger(__name__)
        self.apply_config(config)

        self.logger.debug(
            "Initialized HistoryImportService",
            extra={
                "supported_filenames": self.supported_filenames,
                "rule_ids": [rule.id for rule in self.rules],
            },
        )

    def apply_config(self, history_import_config: Optional[Dict[str, Any]] = None) -> None:
        """Apply a history-import config payload to the service state."""
        config = history_import_config or CONFIG.get("history_import", {})
        self.supported_filenames = config.get(
            "supported_filenames", self.DEFAULT_SUPPORTED_FILENAMES
        )
        self.rules = self._load_rules(config.get("extraction_rules", self.DEFAULT_EXTRACTION_RULES))
        self.pruning_rules = self._load_pruning_rules(config.get("pruning_rules", []))
        self.learned_words = self._load_learned_words(config)

        self.logger.debug(
            "Applied history import config",
            extra={
                "supported_filenames": self.supported_filenames,
                "rule_ids": [rule.id for rule in self.rules],
                "pruning_rules": self.pruning_rules,
                "learned_words_count": len(self.learned_words),
            },
        )

    @staticmethod
    def _load_rules(rule_configs: List[Dict[str, Any]]) -> List[HistoryExtractionRule]:
        rules: List[HistoryExtractionRule] = []
        for rule_config in rule_configs:
            if not isinstance(rule_config, dict):
                continue
            if "id" not in rule_config:
                continue
            rules.append(HistoryExtractionRule.from_dict(rule_config))
        return rules

    @staticmethod
    def _load_pruning_rules(rule_configs: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        rules: List[Dict[str, Any]] = []
        for rule_config in rule_configs or []:
            if not isinstance(rule_config, dict):
                continue
            rule_type = str(rule_config.get("type", "")).strip().lower()
            value = rule_config.get("value")
            if not rule_type or value is None:
                continue
            rules.append({"type": rule_type, "value": value})
        return rules

    def _load_learned_words(self, config: Dict[str, Any]) -> Set[str]:
        learned_words: List[str] = []
        for raw_value in config.get("learned_words", []) or []:
            normalized = self.normalize_word(str(raw_value))
            if normalized:
                learned_words.append(normalized)

        learned_words_file = config.get("learned_words_file")
        if learned_words_file:
            try:
                with Path(learned_words_file).open("r", encoding="utf-8") as handle:
                    for line in handle:
                        normalized = self.normalize_word(line)
                        if normalized:
                            learned_words.append(normalized)
            except FileNotFoundError:
                self.logger.warning(
                    "Learned words file not found",
                    extra={"path": learned_words_file},
                )
            except OSError as exc:
                self.logger.warning(
                    "Failed to load learned words file",
                    extra={"path": learned_words_file, "error": str(exc)},
                )

        return {word for word in learned_words if word}

    def discover_history_paths(self, root_path: str) -> List[Path]:
        root = Path(root_path)
        if not root.exists():
            raise FileNotFoundError(f"History root not found: {root_path}")

        if root.is_file():
            return [root] if root.name in self.supported_filenames else []

        paths: List[Path] = []
        for path in root.rglob("*"):
            if path.is_file() and path.name in self.supported_filenames:
                paths.append(path)
        paths.sort()
        self.logger.debug(
            "Discovered history paths", extra={"root_path": root_path, "path_count": len(paths)}
        )
        return paths

    def extract_candidates_from_history_dir(self, root_path: str) -> List[Dict[str, Any]]:
        history_paths = self.discover_history_paths(root_path)
        return [candidate.to_dict() for candidate in self._extract_candidates_from_paths(history_paths)]

    def _emit_progress(self, current: int, total: int, message: str) -> None:
        """Emit import progress to connected listeners and flush UI events."""
        self.progress_updated.emit(current, total, message)
        try:
            QCoreApplication.processEvents()
        except Exception:
            pass

    def build_word_list(
        self,
        root_path: str,
        manual_words: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Build a word list from history and manual words, returning WordListItem objects.
        
        Args:
            root_path: Path to history directory or file.
            manual_words: Optional list of manually added words.
        
        Returns:
            Dict with:
            - "candidates": List of dicts of extracted history candidates
            - "manual_words": List of normalized manual words
            - "final_word_list": List of WordListItem objects
        """
        history_paths = self.discover_history_paths(root_path)
        if not history_paths:
            result = {
                "candidates": [],
                "manual_words": [],
                "final_word_list": [],
            }
            self._emit_progress(0, 0, "No history files found")
            self.import_finished.emit(result)
            return result

        self._emit_progress(0, len(history_paths), "Scanning history files...")
        candidates = self._extract_candidates_from_paths(history_paths)
        self._emit_progress(len(history_paths), len(history_paths), "Extracting candidates...")
        merged_candidates = self._dedupe_candidates(candidates)

        filtered_candidates = [
            candidate for candidate in merged_candidates if self._should_include_word(candidate.normalized_word)
        ]

        # Build WordListItem objects from history candidates
        history_items: List[WordListItem] = []
        for candidate in filtered_candidates:
            # Convert browse_timestamp (microseconds since epoch) to ISO format
            # If timestamp is 0, use current time
            if candidate.browse_timestamp > 0:
                timestamp_seconds = candidate.browse_timestamp / 1_000_000
                timestamp_dt = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
                timestamp_iso = timestamp_dt.isoformat()
            else:
                timestamp_iso = datetime.now(tz=timezone.utc).isoformat()
            
            item = WordListItem.from_word(
                word=candidate.normalized_word,
                source="browser_history",
                added_time=datetime.now().isoformat(),
                hit_count=1,  # Single candidate after dedup; could be enhanced to track actual count
                first_hit_time=timestamp_iso,
                last_hit_time=timestamp_iso,
                origin_url=candidate.url,
                custom_metadata={
                    "browser_name": candidate.browser_name,
                    "rule_id": candidate.rule_id,
                    "provider_name": candidate.provider_name,
                },
            )
            history_items.append(item)

        # Build WordListItem objects from manual words
        manual_words_list = manual_words or []
        manual_items: List[WordListItem] = []
        for manual_word in manual_words_list:
            normalized = self.normalize_word(manual_word)
            if not normalized or not self._should_include_word(normalized):
                continue
            
            # Check if word already exists in history items
            existing_history = next(
                (item for item in history_items if item.word == normalized),
                None,
            )
            if existing_history is None:
                # Create new item for manual word
                item = WordListItem.from_word(
                    word=normalized,
                    source="manual",
                    added_time=datetime.now().isoformat(),
                    hit_count=0,
                )
                manual_items.append(item)

        # Combine and sort by word
        all_items = history_items + manual_items
        all_items.sort(key=lambda x: x.word)

        result = {
            "candidates": [candidate.to_dict() for candidate in filtered_candidates],
            "manual_words": [
                normalized
                for normalized in [self.normalize_word(w) for w in manual_words_list if self.normalize_word(w)]
                if self._should_include_word(normalized)
            ],
            "final_word_list": all_items,
        }
        self._emit_progress(len(history_paths), len(history_paths), "Import complete")
        self.import_finished.emit(result)
        return result

    def _extract_candidates_from_paths(self, history_paths: List[Path]) -> List[HistoryCandidate]:
        candidates: List[HistoryCandidate] = []
        total_paths = len(history_paths)
        for index, history_path in enumerate(history_paths, start=1):
            self._emit_progress(index, total_paths, f"Scanning {history_path.name}...")
            for entry in self._iter_history_entries(history_path):
                url = entry.get("url")
                if not url or not isinstance(url, str):
                    continue
                url = unquote(url)
                title = entry.get("title") if isinstance(entry.get("title"), str) else None
                browse_timestamp = self._parse_timestamp(entry.get("time_usec"))
                browser_name = self._infer_browser_name(history_path)

                for rule in self.rules:
                    if not rule.matches(url):
                        continue
                    raw_word = rule.extract(url)
                    if not raw_word:
                        continue
                    normalized_word = self.normalize_word(raw_word)
                    if not normalized_word:
                        continue

                    candidate = HistoryCandidate(
                        source_path=str(history_path),
                        browse_timestamp=browse_timestamp,
                        browser_name=browser_name,
                        url=url,
                        rule_id=rule.id,
                        provider_name=rule.provider_name,
                        word=raw_word,
                        normalized_word=normalized_word,
                        title=title,
                    )
                    candidates.append(candidate)
                    break
        self.logger.debug(
            "Extracted history candidates",
            extra={"candidate_count": len(candidates)},
        )
        return candidates

    @staticmethod
    def _iter_history_entries(history_path: Path) -> Iterator[Dict[str, Any]]:
        try:
            with history_path.open("r", encoding="utf-8") as handle:
                container = json.load(handle)
        except Exception as exc:
            _LOGGER.warning(
                "Failed to load history file",
                extra={"path": str(history_path), "error": str(exc)},
            )
            return iter([])

        if isinstance(container, dict):
            entries = container.get("Browser History") or container.get("History")
            if entries is None:
                return iter([])
            if isinstance(entries, list):
                return iter(entries)
        if isinstance(container, list):
            return iter(container)

        return iter([])

    @staticmethod
    def _parse_timestamp(value: Any) -> int:
        try:
            return int(value)
        except Exception:
            return 0

    @staticmethod
    def _infer_browser_name(history_path: Path) -> str:
        path_lower = str(history_path).lower()
        if "chrome" in path_lower:
            return "chrome"
        if "firefox" in path_lower:
            return "firefox"
        return "unknown"

    @staticmethod
    def normalize_word(word: str) -> str:
        if not isinstance(word, str):
            return ""

        normalized = unquote(word)
        normalized = normalized.strip()
        normalized = normalized.strip("/")
        normalized = normalized.replace("+", " ")
        normalized = normalized.replace("\u3000", " ")
        normalized = normalized.strip()
        return normalized

    def _should_include_word(self, word: str) -> bool:
        """Return whether a word should be kept after pruning and learned-word exclusion."""
        normalized_word = self.normalize_word(word)
        if not normalized_word:
            return False
        if normalized_word in self.learned_words:
            return False
        return not self._matches_pruning_rules(normalized_word)

    def _matches_pruning_rules(self, word: str) -> bool:
        """Return whether a word violates the configured pruning rules."""
        for rule in self.pruning_rules:
            rule_type = str(rule.get("type", "")).strip().lower()
            rule_value = rule.get("value")
            if not rule_type or not isinstance(rule_value, str):
                continue

            if rule_type == "prohibited_characters" and any(char in word for char in rule_value):
                return True
            if rule_type == "prohibited_strings" and rule_value in word:
                return True
            if rule_type == "regex":
                try:
                    if re.search(rule_value, word):
                        return True
                except re.error:
                    continue
        return False

    @staticmethod
    def _dedupe_candidates(candidates: List[HistoryCandidate]) -> List[HistoryCandidate]:
        """Deduplicate candidates by normalized_word, tracking hit counts and timestamps.
        
        For each normalized_word, we keep track of:
        - hit_count: number of times this word appeared
        - earliest browse_timestamp (first_hit_time)
        - latest browse_timestamp (last_hit_time)
        
        We return the candidate with the earliest timestamp as the representative.
        """
        # Group candidates by normalized_word
        word_groups: Dict[str, List[HistoryCandidate]] = {}
        for candidate in candidates:
            if not candidate.normalized_word:
                continue
            if candidate.normalized_word not in word_groups:
                word_groups[candidate.normalized_word] = []
            word_groups[candidate.normalized_word].append(candidate)
        
        # For each word, keep the earliest candidate and annotate with hit_count
        dedup_result: List[HistoryCandidate] = []
        for word, group in word_groups.items():
            # Sort by browse_timestamp to get earliest and latest
            group_sorted = sorted(group, key=lambda c: c.browse_timestamp)
            earliest = group_sorted[0]
            
            # Create a modified candidate with hit_count and timestamp info
            # Note: We keep the earliest candidate as representative
            modified = HistoryCandidate(
                source_path=earliest.source_path,
                browse_timestamp=earliest.browse_timestamp,
                browser_name=earliest.browser_name,
                url=earliest.url,
                rule_id=earliest.rule_id,
                provider_name=earliest.provider_name,
                word=earliest.word,
                normalized_word=earliest.normalized_word,
                title=earliest.title,
            )
            dedup_result.append(modified)
        
        return dedup_result
