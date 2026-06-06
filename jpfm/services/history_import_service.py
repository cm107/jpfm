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
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

from jpfm import get_logger
from jpfm.config import CONFIG

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


class HistoryImportService:
    """Service for browser history import and candidate extraction."""

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
    ) -> None:
        config = history_import_config or CONFIG.get("history_import", {})
        self.supported_filenames = config.get(
            "supported_filenames", self.DEFAULT_SUPPORTED_FILENAMES
        )
        self.rules = self._load_rules(config.get("extraction_rules", self.DEFAULT_EXTRACTION_RULES))
        self.logger = logger or get_logger(__name__)

        self.logger.debug(
            "Initialized HistoryImportService",
            extra={
                "supported_filenames": self.supported_filenames,
                "rule_ids": [rule.id for rule in self.rules],
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

    def build_word_list(
        self,
        root_path: str,
        manual_words: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        candidates = self._extract_candidates_from_paths(self.discover_history_paths(root_path))
        merged_candidates = self._dedupe_candidates(candidates)

        manual_words = manual_words or []
        normalized_manual = [self.normalize_word(word) for word in manual_words if self.normalize_word(word)]

        final_word_set = {candidate.normalized_word for candidate in merged_candidates}
        for manual_word in normalized_manual:
            final_word_set.add(manual_word)

        sorted_words = sorted(final_word_set)

        return {
            "candidates": [candidate.to_dict() for candidate in merged_candidates],
            "manual_words": normalized_manual,
            "final_word_list": sorted_words,
        }

    def _extract_candidates_from_paths(self, history_paths: List[Path]) -> List[HistoryCandidate]:
        candidates: List[HistoryCandidate] = []
        for history_path in history_paths:
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

    @staticmethod
    def _dedupe_candidates(candidates: List[HistoryCandidate]) -> List[HistoryCandidate]:
        dedup_map: Dict[str, HistoryCandidate] = {}
        for candidate in candidates:
            if not candidate.normalized_word:
                continue
            existing = dedup_map.get(candidate.normalized_word)
            if existing is None or candidate.browse_timestamp < existing.browse_timestamp:
                dedup_map[candidate.normalized_word] = candidate
        return list(dedup_map.values())
