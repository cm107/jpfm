"""Tests for WordListModel service."""
from datetime import datetime

import pytest
from PySide6.QtCore import Qt

from jpfm.models.word_list_item import WordListItem
from jpfm.services.word_list_model import WordListModel


class TestWordListModelBasicOperations:
    """Test basic WordListModel operations."""

    def test_initialization_empty(self):
        """Test WordListModel initializes empty."""
        model = WordListModel()
        assert model.count() == 0
        assert model.get_items() == []

    def test_add_single_item(self):
        """Test adding a single item."""
        model = WordListModel()
        item = WordListItem.from_word(word="テスト")
        model.add_item(item)

        assert model.count() == 1
        assert model.get_by_word("テスト") == item

    def test_add_multiple_items(self):
        """Test adding multiple items at once."""
        model = WordListModel()
        items = [
            WordListItem.from_word(word="テスト1"),
            WordListItem.from_word(word="テスト2"),
            WordListItem.from_word(word="テスト3"),
        ]
        model.add_items(items)

        assert model.count() == 3
        for item in items:
            assert model.get_by_word(item.word) == item

    def test_add_empty_list_no_error(self):
        """Test adding empty list doesn't cause error."""
        model = WordListModel()
        model.add_items([])
        assert model.count() == 0

    def test_get_items_returns_copy(self):
        """Test that get_items returns a copy, not the internal list."""
        model = WordListModel()
        item = WordListItem.from_word(word="テスト")
        model.add_item(item)

        items = model.get_items()
        # Modifying returned list shouldn't affect model
        items.clear()
        assert model.count() == 1

    def test_remove_item(self):
        """Test removing an item."""
        model = WordListModel()
        item = WordListItem.from_word(word="テスト")
        model.add_item(item)

        model.remove_item("テスト")
        assert model.count() == 0
        assert model.get_by_word("テスト") is None

    def test_remove_nonexistent_item_raises(self):
        """Test removing nonexistent item raises ValueError."""
        model = WordListModel()
        with pytest.raises(ValueError, match="not found"):
            model.remove_item("nonexistent")

    def test_get_by_word_found(self):
        """Test get_by_word returns item when found."""
        model = WordListModel()
        item = WordListItem.from_word(word="テスト", hit_count=5)
        model.add_item(item)

        found = model.get_by_word("テスト")
        assert found == item
        assert found.hit_count == 5

    def test_get_by_word_not_found(self):
        """Test get_by_word returns None when not found."""
        model = WordListModel()
        result = model.get_by_word("nonexistent")
        assert result is None

    def test_clear_all_items(self):
        """Test clearing all items."""
        model = WordListModel()
        items = [
            WordListItem.from_word(word="テスト1"),
            WordListItem.from_word(word="テスト2"),
        ]
        model.add_items(items)
        assert model.count() == 2

        model.clear()
        assert model.count() == 0
        assert model.get_items() == []

    def test_update_existing_item(self):
        """Test that adding item with same word updates it."""
        model = WordListModel()
        item1 = WordListItem.from_word(word="テスト", hit_count=1)
        item2 = WordListItem.from_word(word="テスト", hit_count=5)

        model.add_item(item1)
        assert model.get_by_word("テスト").hit_count == 1

        model.add_item(item2)
        assert model.count() == 1
        assert model.get_by_word("テスト").hit_count == 5


class TestWordListModelMetadataOperations:
    """Test metadata update operations."""

    def test_update_metadata_hit_count(self):
        """Test updating hit_count metadata."""
        model = WordListModel()
        item = WordListItem.from_word(word="テスト", hit_count=1)
        model.add_item(item)

        model.update_metadata("テスト", "hit_count", 10)
        updated = model.get_by_word("テスト")
        assert updated.hit_count == 10

    def test_update_metadata_nonexistent_word(self):
        """Test updating metadata for nonexistent word raises ValueError."""
        model = WordListModel()
        with pytest.raises(ValueError, match="not found"):
            model.update_metadata("nonexistent", "hit_count", 5)

    def test_update_metadata_invalid_field(self):
        """Test updating invalid field raises ValueError."""
        model = WordListModel()
        item = WordListItem.from_word(word="テスト")
        model.add_item(item)

        with pytest.raises(ValueError, match="no field"):
            model.update_metadata("テスト", "invalid_field", "value")

    def test_update_metadata_custom_metadata(self):
        """Test updating custom_metadata dict."""
        model = WordListModel()
        item = WordListItem.from_word(word="テスト")
        model.add_item(item)

        new_metadata = {"browser": "chrome", "count": 5}
        model.update_metadata("テスト", "custom_metadata", new_metadata)
        updated = model.get_by_word("テスト")
        assert updated.custom_metadata == new_metadata


class TestWordListModelSorting:
    """Test sorting operations."""

    def test_sort_by_word(self):
        """Test sorting by word."""
        model = WordListModel()
        items = [
            WordListItem.from_word(word="ゼット"),
            WordListItem.from_word(word="アルファ"),
            WordListItem.from_word(word="ベータ"),
        ]
        model.add_items(items)

        model.sort_by("word")
        sorted_items = model.get_items()
        # Verify items are sorted (in some consistent order, actual order depends on unicode collation)
        words = [item.word for item in sorted_items]
        assert words == sorted(words)

    def test_sort_by_word_reverse(self):
        """Test sorting by word in reverse."""
        model = WordListModel()
        items = [
            WordListItem.from_word(word="ゼット"),
            WordListItem.from_word(word="アルファ"),
            WordListItem.from_word(word="ベータ"),
        ]
        model.add_items(items)

        model.sort_by("word", reverse=True)
        sorted_items = model.get_items()
        # Verify items are sorted in reverse order
        words = [item.word for item in sorted_items]
        assert words == sorted(words, reverse=True)

    def test_sort_by_hit_count(self):
        """Test sorting by hit_count."""
        model = WordListModel()
        items = [
            WordListItem.from_word(word="テスト1", hit_count=5),
            WordListItem.from_word(word="テスト2", hit_count=1),
            WordListItem.from_word(word="テスト3", hit_count=10),
        ]
        model.add_items(items)

        model.sort_by("hit_count")
        sorted_items = model.get_items()
        assert [item.hit_count for item in sorted_items] == [1, 5, 10]

    def test_sort_by_source(self):
        """Test sorting by source."""
        model = WordListModel()
        items = [
            WordListItem.from_word(word="テスト1", source="jisho"),
            WordListItem.from_word(word="テスト2", source="manual"),
            WordListItem.from_word(word="テスト3", source="browser_history"),
        ]
        model.add_items(items)

        model.sort_by("source")
        sorted_items = model.get_items()
        sources = [item.source for item in sorted_items]
        assert sources == ["browser_history", "jisho", "manual"]

    def test_sort_by_last_hit_time_with_none_values(self):
        """Test sorting by last_hit_time with None values."""
        now = datetime.now().isoformat()
        model = WordListModel()
        items = [
            WordListItem.from_word(word="テスト1", last_hit_time=now),
            WordListItem.from_word(word="テスト2", last_hit_time=None),
            WordListItem.from_word(word="テスト3", last_hit_time=now),
        ]
        model.add_items(items)

        model.sort_by("last_hit_time")
        sorted_items = model.get_items()
        # None values should come last
        assert sorted_items[-1].last_hit_time is None

    def test_sort_invalid_criteria(self):
        """Test sorting with invalid criteria raises ValueError."""
        model = WordListModel()
        model.add_item(WordListItem.from_word(word="テスト"))

        with pytest.raises(ValueError, match="Invalid sort criteria"):
            model.sort_by("invalid_criteria")


class TestWordListModelSignals:
    """Test signal emission."""

    def test_items_changed_signal_on_add(self, qtbot):
        """Test items_changed signal is emitted when adding items."""
        model = WordListModel()
        with qtbot.waitSignal(model.items_changed):
            model.add_item(WordListItem.from_word(word="テスト"))

    def test_items_changed_signal_on_remove(self, qtbot):
        """Test items_changed signal is emitted when removing items."""
        model = WordListModel()
        model.add_item(WordListItem.from_word(word="テスト"))

        with qtbot.waitSignal(model.items_changed):
            model.remove_item("テスト")

    def test_items_changed_signal_on_clear(self, qtbot):
        """Test items_changed signal is emitted when clearing."""
        model = WordListModel()
        model.add_item(WordListItem.from_word(word="テスト"))

        with qtbot.waitSignal(model.items_changed):
            model.clear()

    def test_items_changed_signal_on_sort(self, qtbot):
        """Test items_changed signal is emitted on sort."""
        model = WordListModel()
        items = [
            WordListItem.from_word(word="ゼット"),
            WordListItem.from_word(word="アルファ"),
        ]
        model.add_items(items)

        with qtbot.waitSignal(model.items_changed):
            model.sort_by("word")

    def test_metadata_updated_signal(self, qtbot):
        """Test metadata_updated signal is emitted."""
        model = WordListModel()
        model.add_item(WordListItem.from_word(word="テスト"))

        with qtbot.waitSignal(model.metadata_updated):
            model.update_metadata("テスト", "hit_count", 5)

    def test_metadata_updated_signal_on_add_update(self, qtbot):
        """Test metadata_updated signal is emitted when updating existing item."""
        model = WordListModel()
        model.add_item(WordListItem.from_word(word="テスト", hit_count=1))

        with qtbot.waitSignal(model.metadata_updated):
            model.add_item(WordListItem.from_word(word="テスト", hit_count=5))


class TestWordListModelIntegration:
    """Integration tests for common workflows."""

    def test_full_workflow_import_then_add_manual(self):
        """Test complete workflow of importing then adding manual words."""
        model = WordListModel()
        
        # Simulate imported items
        imported = [
            WordListItem.from_word(word="日本", source="browser_history"),
            WordListItem.from_word(word="語", source="browser_history"),
        ]
        model.add_items(imported)

        # Add manual word
        manual = WordListItem.from_word(word="テスト", source="manual")
        model.add_item(manual)

        assert model.count() == 3
        items = model.get_items()
        sources = [item.source for item in items]
        assert sources.count("browser_history") == 2
        assert sources.count("manual") == 1

    def test_remove_and_recount(self):
        """Test removing items and recounting."""
        model = WordListModel()
        items = [
            WordListItem.from_word(word="テスト1"),
            WordListItem.from_word(word="テスト2"),
            WordListItem.from_word(word="テスト3"),
        ]
        model.add_items(items)

        model.remove_item("テスト2")
        assert model.count() == 2
        assert model.get_by_word("テスト2") is None

    def test_sort_then_get_maintains_order(self):
        """Test that sorting is maintained in get_items."""
        model = WordListModel()
        items = [
            WordListItem.from_word(word="ゼット", hit_count=3),
            WordListItem.from_word(word="アルファ", hit_count=1),
            WordListItem.from_word(word="ベータ", hit_count=2),
        ]
        model.add_items(items)

        model.sort_by("hit_count")
        sorted_items = model.get_items()
        
        # Verify order is maintained
        for i in range(len(sorted_items) - 1):
            assert sorted_items[i].hit_count <= sorted_items[i + 1].hit_count
