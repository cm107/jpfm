"""
Unit tests for the StorageService.

Tests cover save/load operations, versioning, error handling, and cache management.
"""

import json
import tempfile
from pathlib import Path

import pytest

from jpfm.storage.storage_service import StorageService, CURRENT_SCHEMA_VERSION


class TestStorageServiceInitialization:
    """Test StorageService initialization and error handling."""

    def test_init_with_valid_base_dir(self):
        """Test initialization with a valid base directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = StorageService(base_dir=tmpdir)
            assert service.base_dir == Path(tmpdir)
            assert service.cache_dir == Path(tmpdir) / "cache"
            assert service.cache_dir.exists()

    def test_init_creates_cache_directory(self):
        """Test that initialization creates the cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = StorageService(base_dir=tmpdir)
            assert service.cache_dir.exists()
            assert service.cache_dir.is_dir()

    def test_init_with_invalid_base_dir_raises_error(self):
        """Test that empty base_dir raises ValueError."""
        with pytest.raises(ValueError):
            StorageService(base_dir="")

    def test_init_with_none_base_dir_raises_error(self):
        """Test that None base_dir raises ValueError."""
        with pytest.raises(ValueError):
            StorageService(base_dir=None)


class TestStorageServiceSaveLoad:
    """Test save and load operations."""

    @pytest.fixture
    def storage_service(self):
        """Create a temporary StorageService for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield StorageService(base_dir=tmpdir)

    def test_save_valid_entry(self, storage_service):
        """Test saving a valid entry to cache."""
        data = {"kanji": "愛", "reading": "あい", "definitions": ["love"]}
        result = storage_service.save("jisho", "愛", data)
        assert result is True

        # Verify file was created
        entry_path = storage_service.cache_dir / "jisho" / "愛.json"
        assert entry_path.exists()

    def test_save_includes_metadata(self, storage_service):
        """Test that saved entries include versioning metadata."""
        data = {"kanji": "愛"}
        storage_service.save("jisho", "愛", data)

        entry_path = storage_service.cache_dir / "jisho" / "愛.json"
        with open(entry_path, "r", encoding="utf-8") as f:
            saved_entry = json.load(f)

        assert saved_entry["_version"] == CURRENT_SCHEMA_VERSION
        assert saved_entry["_source"] == "jisho"
        assert "_cached_at" in saved_entry
        assert saved_entry["kanji"] == "愛"

    def test_save_with_empty_dict_raises_error(self, storage_service):
        """Test that saving an empty dictionary raises ValueError."""
        with pytest.raises(ValueError):
            storage_service.save("jisho", "愛", {})

    def test_load_valid_entry(self, storage_service):
        """Test loading a valid cached entry."""
        original_data = {"kanji": "愛", "reading": "あい"}
        storage_service.save("jisho", "愛", original_data)

        loaded_data = storage_service.load("jisho", "愛")
        assert loaded_data is not None
        assert loaded_data["kanji"] == "愛"
        assert loaded_data["reading"] == "あい"

    def test_load_does_not_include_metadata(self, storage_service):
        """Test that loaded data excludes internal metadata fields."""
        data = {"kanji": "愛"}
        storage_service.save("jisho", "愛", data)

        loaded_data = storage_service.load("jisho", "愛")
        assert "_version" not in loaded_data
        assert "_source" not in loaded_data
        assert "_cached_at" not in loaded_data

    def test_load_nonexistent_entry_returns_none(self, storage_service):
        """Test that loading a non-existent entry returns None."""
        result = storage_service.load("jisho", "nonexistent")
        assert result is None

    def test_load_legacy_entry_migrates_and_returns_data(self, storage_service):
        """Test that loading a legacy entry migrates it to the current schema."""
        # Manually create a legacy cache entry
        entry_path = storage_service.cache_dir / "jisho" / "愛.json"
        entry_path.parent.mkdir(parents=True, exist_ok=True)

        legacy_entry = {
            "_version": "0.5",  # Old version
            "_source": "jisho",
            "kanji": "愛",
            "reading": "あい",
        }
        with open(entry_path, "w", encoding="utf-8") as f:
            json.dump(legacy_entry, f)

        result = storage_service.load("jisho", "愛")
        assert result is not None
        assert result["kanji"] == "愛"
        assert result["reading"] == "あい"

        with open(entry_path, "r", encoding="utf-8") as f:
            migrated_entry = json.load(f)

        assert migrated_entry["_version"] == CURRENT_SCHEMA_VERSION
        assert migrated_entry["_source"] == "jisho"
        assert "_cached_at" in migrated_entry

    def test_load_entry_without_version_migrates(self, storage_service):
        """Test that entries missing `_version` are treated as legacy and migrated."""
        entry_path = storage_service.cache_dir / "jisho" / "音.json"
        entry_path.parent.mkdir(parents=True, exist_ok=True)

        legacy_entry = {"kanji": "音", "reading": "おん"}
        with open(entry_path, "w", encoding="utf-8") as f:
            json.dump(legacy_entry, f)

        result = storage_service.load("jisho", "音")
        assert result is not None
        assert result["kanji"] == "音"
        assert result["reading"] == "おん"

        with open(entry_path, "r", encoding="utf-8") as f:
            migrated_entry = json.load(f)

        assert migrated_entry["_version"] == CURRENT_SCHEMA_VERSION
        assert migrated_entry["_source"] == "jisho"
        assert "_cached_at" in migrated_entry


class TestStorageServiceExists:
    """Test existence checking."""

    @pytest.fixture
    def storage_service(self):
        """Create a temporary StorageService for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield StorageService(base_dir=tmpdir)

    def test_exists_valid_entry(self, storage_service):
        """Test that exists returns True for valid cached entries."""
        storage_service.save("jisho", "愛", {"kanji": "愛"})
        assert storage_service.exists("jisho", "愛") is True

    def test_exists_nonexistent_entry(self, storage_service):
        """Test that exists returns False for non-existent entries."""
        assert storage_service.exists("jisho", "nonexistent") is False

    def test_exists_legacy_entry_returns_true(self, storage_service):
        """Test that exists returns True for legacy entries that can be migrated."""
        # Manually create a legacy entry
        entry_path = storage_service.cache_dir / "jisho" / "愛.json"
        entry_path.parent.mkdir(parents=True, exist_ok=True)

        legacy_entry = {
            "_version": "0.5",  # Old version
            "kanji": "愛",
        }
        with open(entry_path, "w", encoding="utf-8") as f:
            json.dump(legacy_entry, f)

        assert storage_service.exists("jisho", "愛") is True


class TestStorageServiceListCachedWords:
    """Test listing cached words."""

    @pytest.fixture
    def storage_service(self):
        """Create a temporary StorageService for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield StorageService(base_dir=tmpdir)

    def test_list_cached_words_empty(self, storage_service):
        """Test listing when no entries are cached."""
        result = storage_service.list_cached_words("jisho")
        assert result == []

    def test_list_cached_words_multiple_entries(self, storage_service):
        """Test listing multiple cached entries."""
        storage_service.save("jisho", "愛", {"kanji": "愛"})
        storage_service.save("jisho", "行", {"kanji": "行"})
        storage_service.save("jisho", "音", {"kanji": "音"})

        result = storage_service.list_cached_words("jisho")
        assert len(result) == 3
        assert "愛" in result
        assert "行" in result
        assert "音" in result
        # Verify sorted order
        assert result == sorted(result)

    def test_list_cached_words_includes_legacy_entries(self, storage_service):
        """Test that listing includes legacy entries that can be migrated."""
        # Save a valid entry
        storage_service.save("jisho", "愛", {"kanji": "愛"})

        # Manually create a legacy entry
        entry_path = storage_service.cache_dir / "jisho" / "行.json"
        entry_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_entry = {"_version": "0.5", "kanji": "行"}
        with open(entry_path, "w", encoding="utf-8") as f:
            json.dump(legacy_entry, f)

        result = storage_service.list_cached_words("jisho")
        assert len(result) == 2
        assert "愛" in result
        assert "行" in result

    def test_list_cached_words_nonexistent_source(self, storage_service):
        """Test listing for a source with no cache directory."""
        result = storage_service.list_cached_words("nonexistent_source")
        assert result == []


class TestStorageServiceClearCache:
    """Test cache clearing."""

    @pytest.fixture
    def storage_service(self):
        """Create a temporary StorageService for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield StorageService(base_dir=tmpdir)

    def test_clear_specific_source(self, storage_service):
        """Test clearing cache for a specific source."""
        storage_service.save("jisho", "愛", {"kanji": "愛"})
        storage_service.save("kotobank", "愛", {"title": "愛"})

        storage_service.clear_cache(source="jisho")

        # Jisho cache should be cleared
        assert storage_service.list_cached_words("jisho") == []
        # Kotobank cache should remain
        assert storage_service.exists("kotobank", "愛") is True

    def test_clear_all_cache(self, storage_service):
        """Test clearing all cache."""
        storage_service.save("jisho", "愛", {"kanji": "愛"})
        storage_service.save("kotobank", "愛", {"title": "愛"})
        storage_service.save("koohii", "愛", {"mnemonic": "love"})

        storage_service.clear_cache()

        # All caches should be cleared
        assert storage_service.list_cached_words("jisho") == []
        assert storage_service.list_cached_words("kotobank") == []
        assert storage_service.list_cached_words("koohii") == []


class TestStorageServiceErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def storage_service(self):
        """Create a temporary StorageService for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield StorageService(base_dir=tmpdir)

    def test_get_entry_path_with_invalid_source(self, storage_service):
        """Test that invalid source raises ValueError."""
        with pytest.raises(ValueError):
            storage_service._get_entry_path("", "愛")

    def test_get_entry_path_with_invalid_word(self, storage_service):
        """Test that invalid word raises ValueError."""
        with pytest.raises(ValueError):
            storage_service._get_entry_path("jisho", "")

    def test_save_invalid_parsed_data_type(self, storage_service):
        """Test that saving non-dict data raises ValueError."""
        with pytest.raises(ValueError):
            storage_service.save("jisho", "愛", "invalid_data")

    def test_unicode_word_handling(self, storage_service):
        """Test that unicode characters in words are handled correctly."""
        data = {"kanji": "日本語"}
        result = storage_service.save("jisho", "日本語", data)
        assert result is True

        loaded = storage_service.load("jisho", "日本語")
        assert loaded["kanji"] == "日本語"
