"""
Unit tests for the DictionaryManager service.

Tests cover cache-aware lookups, batch operations, and integration
with parsers and storage layers.
"""

import tempfile
from unittest.mock import Mock, MagicMock, patch

import pytest

from jpfm.services.dictionary_manager import DictionaryManager
from jpfm.storage import StorageService


class TestDictionaryManagerInitialization:
    """Test DictionaryManager initialization and setup."""

    def test_init_with_default_storage(self):
        """Test initialization with auto-created storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DictionaryManager(base_dir=tmpdir)
            assert manager.storage is not None
            assert isinstance(manager.storage, StorageService)
            assert len(manager.factories) == 3
            assert "jisho" in manager.factories
            assert "kotobank" in manager.factories
            assert "koohii" in manager.factories

    def test_init_with_provided_storage(self):
        """Test initialization with pre-configured storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageService(base_dir=tmpdir)
            manager = DictionaryManager(storage=storage)
            assert manager.storage is storage

    def test_supported_sources_constant(self):
        """Test that supported sources are correctly defined."""
        assert DictionaryManager.SUPPORTED_SOURCES == [
            "jisho",
            "kotobank",
            "koohii",
        ]


class TestDictionaryManagerValidation:
    """Test source and input validation."""

    @pytest.fixture
    def manager(self):
        """Create a temporary DictionaryManager for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield DictionaryManager(base_dir=tmpdir)

    def test_validate_source_valid(self, manager):
        """Test that valid sources pass validation."""
        # Should not raise
        manager._validate_source("jisho")
        manager._validate_source("kotobank")
        manager._validate_source("koohii")

    def test_validate_source_invalid(self, manager):
        """Test that invalid source raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported source"):
            manager._validate_source("invalid_source")

    def test_get_entry_empty_word_raises_error(self, manager):
        """Test that empty word raises ValueError."""
        with pytest.raises(ValueError, match="word must be a non-empty string"):
            manager.get_entry("jisho", "")

    def test_get_entry_invalid_source_raises_error(self, manager):
        """Test that invalid source raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported source"):
            manager.get_entry("invalid", "愛")

    def test_batch_get_entries_empty_words_raises_error(self, manager):
        """Test that empty word list raises ValueError."""
        with pytest.raises(ValueError, match="words must be a non-empty list"):
            manager.batch_get_entries("jisho", [])

    def test_batch_get_entries_invalid_source_raises_error(self, manager):
        """Test that invalid source raises ValueError for batch."""
        with pytest.raises(ValueError, match="Unsupported source"):
            manager.batch_get_entries("invalid", ["愛"])

    def test_clear_cache_invalid_source_raises_error(self, manager):
        """Test that invalid source raises ValueError for clear."""
        with pytest.raises(ValueError, match="Unsupported source"):
            manager.clear_cache(source="invalid")

    def test_list_cached_words_invalid_source_raises_error(self, manager):
        """Test that invalid source raises ValueError for listing."""
        with pytest.raises(ValueError, match="Unsupported source"):
            manager.list_cached_words("invalid")


class TestDictionaryManagerCacheHit:
    """Test cache hit scenarios."""

    @pytest.fixture
    def manager(self):
        """Create a temporary DictionaryManager for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield DictionaryManager(base_dir=tmpdir)

    def test_get_entry_cache_hit(self, manager):
        """Test that cached entries are returned without parsing."""
        # Pre-populate cache
        cached_data = {"kanji": "愛", "reading": "あい", "definitions": ["love"]}
        manager.storage.save("jisho", "愛", cached_data)

        # Mock the factory's fetch to verify it's not called
        manager.factories["jisho"].fetch_html = Mock()

        # Retrieve entry
        result = manager.get_entry("jisho", "愛")

        # Should return cached data without calling fetch
        assert result == cached_data
        manager.factories["jisho"].fetch_html.assert_not_called()

    def test_get_entry_cache_hit_multiple_sources(self, manager):
        """Test cache hits work independently across sources."""
        jisho_data = {"kanji": "愛", "source": "jisho"}
        kotobank_data = {"title": "愛", "source": "kotobank"}

        manager.storage.save("jisho", "愛", jisho_data)
        manager.storage.save("kotobank", "愛", kotobank_data)

        # Should return correct data for each source
        assert manager.get_entry("jisho", "愛") == jisho_data
        assert manager.get_entry("kotobank", "愛") == kotobank_data


class TestDictionaryManagerCacheMiss:
    """Test cache miss scenarios with parsing."""

    @pytest.fixture
    def manager(self):
        """Create a temporary DictionaryManager for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield DictionaryManager(base_dir=tmpdir)

    def test_get_entry_cache_miss_parses_and_caches(self, manager):
        """Test that cache misses trigger parsing and save result."""
        parsed_data = {"kanji": "愛", "reading": "あい"}

        # Mock the factory to return a mock parser
        mock_parser = Mock()
        mock_parser.parse = Mock(return_value=parsed_data)

        manager.factories["jisho"].fetch_html = Mock(return_value="<html>test</html>")
        manager.factories["jisho"].create_parser = Mock(return_value=mock_parser)
        manager.factories["jisho"].get_url = Mock(return_value="http://jisho.org/search/愛")

        # Retrieve entry (cache miss)
        result = manager.get_entry("jisho", "愛")

        # Should call fetch
        manager.factories["jisho"].fetch_html.assert_called_once_with("愛")

        # Should create parser with fetched HTML
        manager.factories["jisho"].create_parser.assert_called_once()

        # Should call parse
        mock_parser.parse.assert_called_once()

        # Should return parsed data
        assert result == parsed_data

        # Should be cached now
        assert manager.storage.exists("jisho", "愛")
        cached = manager.storage.load("jisho", "愛")
        assert cached == parsed_data

    def test_get_entry_fetch_returns_none(self, manager):
        """Test handling when fetching returns None."""
        manager.factories["jisho"].fetch_html = Mock(return_value=None)

        result = manager.get_entry("jisho", "nonexistent")
        assert result is None

    def test_get_entry_parser_returns_none(self, manager):
        """Test handling when parser returns None."""
        mock_parser = Mock()
        mock_parser.parse = Mock(return_value=None)

        manager.factories["jisho"].fetch_html = Mock(return_value="<html>test</html>")
        manager.factories["jisho"].create_parser = Mock(return_value=mock_parser)
        manager.factories["jisho"].get_url = Mock(return_value="http://jisho.org/search/愛")

        result = manager.get_entry("jisho", "愛")
        assert result is None

    def test_get_entry_parser_raises_exception(self, manager):
        """Test handling when parser raises an exception."""
        manager.factories["jisho"].fetch_html = Mock(
            side_effect=Exception("Network error")
        )

        result = manager.get_entry("jisho", "愛")
        assert result is None

    def test_get_entry_different_sources_use_different_factories(self, manager):
        """Test that different sources use their respective factories."""
        mock_jisho_parser = Mock()
        mock_jisho_parser.parse = Mock(return_value={"source": "jisho"})

        mock_kotobank_parser = Mock()
        mock_kotobank_parser.parse = Mock(return_value={"source": "kotobank"})

        manager.factories["jisho"].fetch_html = Mock(return_value="<html>jisho</html>")
        manager.factories["jisho"].create_parser = Mock(return_value=mock_jisho_parser)
        manager.factories["jisho"].get_url = Mock(return_value="http://jisho.org/search/愛")

        manager.factories["kotobank"].fetch_html = Mock(return_value="<html>kotobank</html>")
        manager.factories["kotobank"].create_parser = Mock(return_value=mock_kotobank_parser)
        manager.factories["kotobank"].get_url = Mock(return_value="http://kotobank.jp/word/愛")

        manager.get_entry("jisho", "愛")
        manager.get_entry("kotobank", "愛")

        manager.factories["jisho"].fetch_html.assert_called_once_with("愛")
        manager.factories["kotobank"].fetch_html.assert_called_once_with("愛")


class TestDictionaryManagerBatchOperations:
    """Test batch lookup operations."""

    @pytest.fixture
    def manager(self):
        """Create a temporary DictionaryManager for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield DictionaryManager(base_dir=tmpdir)

    def test_batch_get_entries_all_cache_hits(self, manager):
        """Test batch retrieval when all entries are cached."""
        words = ["愛", "行", "音"]
        for word in words:
            manager.storage.save("jisho", word, {"kanji": word})

        # Mock factory to verify it's not called
        manager.factories["jisho"].fetch_html = Mock()

        result = manager.batch_get_entries("jisho", words)

        assert len(result) == 3
        manager.factories["jisho"].fetch_html.assert_not_called()

    def test_batch_get_entries_all_cache_misses(self, manager):
        """Test batch retrieval when all entries need parsing."""
        words = ["愛", "行", "音"]

        def create_parser_side_effect(html, url):
            parser = Mock()
            # Extract word from URL for testing
            word = url.split("/")[-1]
            parser.parse = Mock(return_value={"kanji": word, "parsed": True})
            return parser

        manager.factories["jisho"].fetch_html = Mock(return_value="<html>test</html>")
        manager.factories["jisho"].create_parser = Mock(side_effect=create_parser_side_effect)
        manager.factories["jisho"].get_url = Mock(side_effect=lambda w: f"http://jisho.org/search/{w}")

        result = manager.batch_get_entries("jisho", words)

        assert len(result) == 3
        assert manager.factories["jisho"].fetch_html.call_count == 3

        # All should be cached now
        for word in words:
            assert manager.storage.exists("jisho", word)

    def test_batch_get_entries_mixed_hits_and_misses(self, manager):
        """Test batch retrieval with mixture of cached and uncached entries."""
        # Cache first two words
        manager.storage.save("jisho", "愛", {"kanji": "愛", "cached": True})
        manager.storage.save("jisho", "行", {"kanji": "行", "cached": True})

        words = ["愛", "行", "音"]

        def create_parser_side_effect(html, url):
            parser = Mock()
            parser.parse = Mock(return_value={"kanji": "音", "parsed": True})
            return parser

        manager.factories["jisho"].fetch_html = Mock(return_value="<html>test</html>")
        manager.factories["jisho"].create_parser = Mock(side_effect=create_parser_side_effect)
        manager.factories["jisho"].get_url = Mock(side_effect=lambda w: f"http://jisho.org/search/{w}")

        result = manager.batch_get_entries("jisho", words)

        # Should return all 3 entries
        assert len(result) == 3

        # Should only fetch the uncached one
        manager.factories["jisho"].fetch_html.assert_called_once_with("音")

    def test_batch_get_entries_filters_none_results(self, manager):
        """Test that failed lookups (None results) are filtered out."""
        words = ["愛", "行", "nonexistent"]

        def create_parser_side_effect(html, url):
            parser = Mock()
            word = url.split("/")[-1]
            if word == "nonexistent":
                parser.parse = Mock(return_value=None)
            else:
                parser.parse = Mock(return_value={"kanji": word})
            return parser

        manager.factories["jisho"].fetch_html = Mock(return_value="<html>test</html>")
        manager.factories["jisho"].create_parser = Mock(side_effect=create_parser_side_effect)
        manager.factories["jisho"].get_url = Mock(side_effect=lambda w: f"http://jisho.org/search/{w}")

        result = manager.batch_get_entries("jisho", words)

        # Should return 2 entries (nonexistent filtered)
        assert len(result) == 2


class TestDictionaryManagerCacheManagement:
    """Test cache clearing and statistics."""

    @pytest.fixture
    def manager(self):
        """Create a temporary DictionaryManager for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield DictionaryManager(base_dir=tmpdir)

    def test_clear_cache_specific_source(self, manager):
        """Test clearing cache for a specific source."""
        # Populate cache across sources
        manager.storage.save("jisho", "愛", {"kanji": "愛"})
        manager.storage.save("kotobank", "愛", {"title": "愛"})

        # Clear only jisho
        result = manager.clear_cache(source="jisho")
        assert result is True

        # Jisho should be empty
        assert len(manager.list_cached_words("jisho")) == 0

        # Kotobank should still have data
        assert len(manager.list_cached_words("kotobank")) == 1

    def test_clear_cache_all_sources(self, manager):
        """Test clearing all cache."""
        manager.storage.save("jisho", "愛", {"kanji": "愛"})
        manager.storage.save("kotobank", "愛", {"title": "愛"})
        manager.storage.save("koohii", "愛", {"mnemonic": "love"})

        result = manager.clear_cache()
        assert result is True

        # All should be empty
        for source in DictionaryManager.SUPPORTED_SOURCES:
            assert len(manager.list_cached_words(source)) == 0

    def test_list_cached_words(self, manager):
        """Test listing cached words for a source."""
        words = ["愛", "行", "音"]
        for word in words:
            manager.storage.save("jisho", word, {"kanji": word})

        result = manager.list_cached_words("jisho")
        assert set(result) == set(words)
        assert result == sorted(result)  # Should be sorted

    def test_get_cache_stats_empty(self, manager):
        """Test cache stats when no entries are cached."""
        stats = manager.get_cache_stats()

        assert len(stats) == 3
        assert all(count == 0 for count in stats.values())

    def test_get_cache_stats_with_entries(self, manager):
        """Test cache stats with entries across sources."""
        manager.storage.save("jisho", "愛", {"kanji": "愛"})
        manager.storage.save("jisho", "行", {"kanji": "行"})
        manager.storage.save("kotobank", "愛", {"title": "愛"})

        stats = manager.get_cache_stats()

        assert stats["jisho"] == 2
        assert stats["kotobank"] == 1
        assert stats["koohii"] == 0


class TestDictionaryManagerIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def manager(self):
        """Create a temporary DictionaryManager for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield DictionaryManager(base_dir=tmpdir)

    def test_workflow_lookup_and_cache_reuse(self, manager):
        """Test complete workflow: lookup -> cache -> reuse."""
        parsed_data = {"kanji": "愛", "reading": "あい"}

        mock_parser = Mock()
        mock_parser.parse = Mock(return_value=parsed_data)

        manager.factories["jisho"].fetch_html = Mock(return_value="<html>test</html>")
        manager.factories["jisho"].create_parser = Mock(return_value=mock_parser)
        manager.factories["jisho"].get_url = Mock(return_value="http://jisho.org/search/愛")

        # First lookup (cache miss)
        result1 = manager.get_entry("jisho", "愛")
        assert result1 == parsed_data
        assert manager.factories["jisho"].fetch_html.call_count == 1

        # Second lookup (cache hit)
        result2 = manager.get_entry("jisho", "愛")
        assert result2 == parsed_data
        assert manager.factories["jisho"].fetch_html.call_count == 1  # Not called again

    def test_workflow_batch_then_check_cache(self, manager):
        """Test that batch operations populate cache for reuse."""

        def create_parser_side_effect(html, url):
            parser = Mock()
            word = url.split("/")[-1]
            parser.parse = Mock(return_value={"kanji": word})
            return parser

        manager.factories["jisho"].fetch_html = Mock(return_value="<html>test</html>")
        manager.factories["jisho"].create_parser = Mock(side_effect=create_parser_side_effect)
        manager.factories["jisho"].get_url = Mock(side_effect=lambda w: f"http://jisho.org/search/{w}")

        # Batch lookup (cache misses)
        words = ["愛", "行"]
        manager.batch_get_entries("jisho", words)

        # Verify all are cached
        for word in words:
            assert manager.storage.exists("jisho", word)

        # Second lookup should be cache hit
        manager.factories["jisho"].fetch_html.reset_mock()
        manager.get_entry("jisho", "愛")
        manager.factories["jisho"].fetch_html.assert_not_called()

    def test_workflow_cross_source_cache_independence(self, manager):
        """Test that caches are independent across sources."""
        jisho_data = {"source": "jisho"}
        kotobank_data = {"source": "kotobank"}

        jisho_parser = Mock()
        jisho_parser.parse = Mock(return_value=jisho_data)

        kotobank_parser = Mock()
        kotobank_parser.parse = Mock(return_value=kotobank_data)

        manager.factories["jisho"].fetch_html = Mock(return_value="<html>jisho</html>")
        manager.factories["jisho"].create_parser = Mock(return_value=jisho_parser)
        manager.factories["jisho"].get_url = Mock(return_value="http://jisho.org/search/愛")

        manager.factories["kotobank"].fetch_html = Mock(return_value="<html>kotobank</html>")
        manager.factories["kotobank"].create_parser = Mock(return_value=kotobank_parser)
        manager.factories["kotobank"].get_url = Mock(return_value="http://kotobank.jp/word/愛")

        # Get from both sources
        manager.get_entry("jisho", "愛")
        manager.get_entry("kotobank", "愛")

        # Clear jisho
        manager.clear_cache(source="jisho")

        # Kotobank should still have entry
        assert manager.storage.exists("kotobank", "愛")
        assert not manager.storage.exists("jisho", "愛")
