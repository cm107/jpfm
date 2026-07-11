"""Tests for WordListItem model."""
from datetime import datetime

import pytest

from jpfm.models.word_list_item import WordListItem


class TestWordListItemCreation:
    """Test WordListItem creation and validation."""

    def test_create_minimal_item(self):
        """Test creating a WordListItem with minimal required fields."""
        now_iso = datetime.now().isoformat()
        item = WordListItem(
            word="テスト",
            source="manual",
            added_time=now_iso,
        )
        assert item.word == "テスト"
        assert item.source == "manual"
        assert item.added_time == now_iso
        assert item.hit_count == 0
        assert item.origin_url is None

    def test_create_full_item(self):
        """Test creating a WordListItem with all fields."""
        now_iso = datetime.now().isoformat()
        item = WordListItem(
            word="漢字",
            source="browser_history",
            added_time=now_iso,
            hit_count=5,
            first_hit_time=now_iso,
            last_hit_time=now_iso,
            origin_url="https://example.com",
            custom_metadata={"key": "value"},
        )
        assert item.word == "漢字"
        assert item.hit_count == 5
        assert item.custom_metadata == {"key": "value"}

    def test_from_word_factory_method(self):
        """Test WordListItem.from_word factory method."""
        item = WordListItem.from_word(word="単語", source="manual")
        assert item.word == "単語"
        assert item.source == "manual"
        assert item.added_time is not None
        assert item.hit_count == 0

    def test_from_word_with_custom_metadata(self):
        """Test from_word with custom metadata."""
        metadata = {"browser": "chrome", "count": 10}
        item = WordListItem.from_word(
            word="日本語",
            source="browser_history",
            hit_count=10,
            custom_metadata=metadata,
        )
        assert item.custom_metadata == metadata

    def test_word_list_item_is_frozen(self):
        """Test that WordListItem is immutable (frozen)."""
        item = WordListItem.from_word(word="テスト")
        with pytest.raises(AttributeError):
            item.word = "別の単語"  # type: ignore

    def test_invalid_empty_word(self):
        """Test that empty word raises ValueError."""
        with pytest.raises(ValueError, match="word must not be empty"):
            WordListItem(
                word="",
                source="manual",
                added_time=datetime.now().isoformat(),
            )

    def test_invalid_whitespace_only_word(self):
        """Test that whitespace-only word raises ValueError."""
        with pytest.raises(ValueError, match="word must not be empty"):
            WordListItem(
                word="   ",
                source="manual",
                added_time=datetime.now().isoformat(),
            )

    def test_invalid_timestamp_format(self):
        """Test that invalid ISO format timestamp raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ISO format timestamp"):
            WordListItem(
                word="テスト",
                source="manual",
                added_time="not-a-timestamp",
            )

    def test_invalid_first_hit_time_format(self):
        """Test that invalid first_hit_time format raises ValueError."""
        now_iso = datetime.now().isoformat()
        with pytest.raises(ValueError, match="Invalid ISO format timestamp"):
            WordListItem(
                word="テスト",
                source="manual",
                added_time=now_iso,
                first_hit_time="invalid",
            )

    def test_none_timestamps_allowed(self):
        """Test that None is allowed for optional timestamps."""
        now_iso = datetime.now().isoformat()
        item = WordListItem(
            word="テスト",
            source="manual",
            added_time=now_iso,
            first_hit_time=None,
            last_hit_time=None,
        )
        assert item.first_hit_time is None
        assert item.last_hit_time is None

    def test_equality(self):
        """Test WordListItem equality."""
        now_iso = datetime.now().isoformat()
        item1 = WordListItem(
            word="テスト",
            source="manual",
            added_time=now_iso,
        )
        item2 = WordListItem(
            word="テスト",
            source="manual",
            added_time=now_iso,
        )
        assert item1 == item2

    def test_inequality_different_word(self):
        """Test inequality with different word."""
        now_iso = datetime.now().isoformat()
        item1 = WordListItem(
            word="テスト",
            source="manual",
            added_time=now_iso,
        )
        item2 = WordListItem(
            word="テスト2",
            source="manual",
            added_time=now_iso,
        )
        assert item1 != item2


class TestWordListItemEdgeCases:
    """Test edge cases for WordListItem."""

    def test_unicode_word(self):
        """Test handling of various Unicode words."""
        words = ["日本語", "テスト", "漢字", "ひらがな", "カタカナ"]
        for word in words:
            item = WordListItem.from_word(word=word)
            assert item.word == word

    def test_hit_count_zero(self):
        """Test hit_count of 0."""
        item = WordListItem.from_word(word="テスト", hit_count=0)
        assert item.hit_count == 0

    def test_hit_count_large(self):
        """Test large hit_count."""
        item = WordListItem.from_word(word="テスト", hit_count=999999)
        assert item.hit_count == 999999

    def test_url_with_special_characters(self):
        """Test URL with special characters."""
        url = "https://example.com/search?q=%E3%83%86%E3%82%B9%E3%83%88"
        item = WordListItem.from_word(word="テスト", origin_url=url)
        assert item.origin_url == url

    def test_empty_custom_metadata_default(self):
        """Test that custom_metadata defaults to empty dict."""
        item = WordListItem.from_word(word="テスト")
        assert item.custom_metadata == {}
        assert isinstance(item.custom_metadata, dict)
