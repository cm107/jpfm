"""
Unit tests for the HistoryImportService.

These tests validate recursive history discovery, URL extraction rules,
normalization, deduplication, and manual word merge behavior.
"""

import json
from pathlib import Path

import pytest

from jpfm.services.history_import_service import HistoryImportService


class TestHistoryImportService:
    def test_discover_history_paths_recursively(self, tmp_path):
        root = tmp_path / "history_root"
        nested = root / "nested"
        nested.mkdir(parents=True)

        browser_history = root / "BrowserHistory.json"
        history_file = nested / "History.json"
        unrelated = root / "README.txt"

        browser_history.write_text("{}", encoding="utf-8")
        history_file.write_text("{}", encoding="utf-8")
        unrelated.write_text("ignore me", encoding="utf-8")

        service = HistoryImportService(
            history_import_config={
                "supported_filenames": ["BrowserHistory.json", "History.json"],
                "extraction_rules": [],
            }
        )

        paths = service.discover_history_paths(str(root))

        assert len(paths) == 2
        assert browser_history in paths
        assert history_file in paths

    def test_extract_candidates_from_history_dir(self, tmp_path):
        root = tmp_path / "history_root"
        root.mkdir()

        entry = {
            "title": "食べる - Jisho",
            "url": "https://jisho.org/search/食べる",
            "client_id": "1",
            "time_usec": 1234567890,
        }
        data = {"Browser History": [entry]}

        history_file = root / "BrowserHistory.json"
        history_file.write_text(json.dumps(data), encoding="utf-8")

        service = HistoryImportService(
            history_import_config={
                "supported_filenames": ["BrowserHistory.json", "History.json"],
                "extraction_rules": [
                    {
                        "id": "jisho_search",
                        "provider_name": "jisho",
                        "matcher": {"type": "prefix", "value": "https://jisho.org/search/"},
                        "extractor": {"type": "path_prefix", "value": "/search/"},
                    }
                ],
            }
        )

        candidates = service.extract_candidates_from_history_dir(str(root))

        assert len(candidates) == 1
        candidate = candidates[0]
        assert candidate["rule_id"] == "jisho_search"
        assert candidate["provider_name"] == "jisho"
        assert candidate["word"] == "食べる"
        assert candidate["normalized_word"] == "食べる"
        assert candidate["source_path"] == str(history_file)
        assert candidate["browse_timestamp"] == 1234567890
        assert candidate["title"] == "食べる - Jisho"

    def test_build_word_list_merges_manual_words_and_dedupes(self, tmp_path):
        root = tmp_path / "history_root"
        root.mkdir()

        entries = [
            {
                "title": "食べる - Jisho",
                "url": "https://jisho.org/search/食べる",
                "client_id": "1",
                "time_usec": 100,
            },
            {
                "title": "食べる - Jisho",
                "url": "https://jisho.org/search/食べる",
                "client_id": "2",
                "time_usec": 200,
            },
        ]
        history_file = root / "BrowserHistory.json"
        history_file.write_text(json.dumps({"Browser History": entries}), encoding="utf-8")

        service = HistoryImportService(
            history_import_config={
                "supported_filenames": ["BrowserHistory.json", "History.json"],
                "extraction_rules": [
                    {
                        "id": "jisho_search",
                        "provider_name": "jisho",
                        "matcher": {"type": "prefix", "value": "https://jisho.org/search/"},
                        "extractor": {"type": "path_prefix", "value": "/search/"},
                    }
                ],
            }
        )

        result = service.build_word_list(str(root), manual_words=["食べる", "動く"])

        assert result["final_word_list"] == ["動く", "食べる"]
        assert result["manual_words"] == ["食べる", "動く"]
        assert len(result["candidates"]) == 1
        assert result["candidates"][0]["normalized_word"] == "食べる"

    def test_extract_candidates_skips_unsupported_urls(self, tmp_path):
        root = tmp_path / "history_root"
        root.mkdir()

        entry = {
            "title": "Not Jisho",
            "url": "https://example.com/search/食べる",
            "client_id": "1",
            "time_usec": 1234567890,
        }
        history_file = root / "BrowserHistory.json"
        history_file.write_text(json.dumps({"Browser History": [entry]}), encoding="utf-8")

        service = HistoryImportService(
            history_import_config={
                "supported_filenames": ["BrowserHistory.json", "History.json"],
                "extraction_rules": [
                    {
                        "id": "jisho_search",
                        "provider_name": "jisho",
                        "matcher": {"type": "prefix", "value": "https://jisho.org/search/"},
                        "extractor": {"type": "path_prefix", "value": "/search/"},
                    }
                ],
            }
        )

        candidates = service.extract_candidates_from_history_dir(str(root))
        assert candidates == []

    def test_discover_history_paths_missing_root_raises(self):
        service = HistoryImportService(
            history_import_config={
                "supported_filenames": ["BrowserHistory.json", "History.json"],
                "extraction_rules": [],
            }
        )
        with pytest.raises(FileNotFoundError):
            service.discover_history_paths("/path/does/not/exist")
