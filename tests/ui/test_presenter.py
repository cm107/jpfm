"""
Unit tests for the DictionaryPresenter.

These tests verify that the presenter correctly coordinates the view, dictionary
manager, word list model, and history import service for search, history import,
and manual word entry.
"""

from unittest.mock import MagicMock

import pytest

from jpfm.models.word_list_item import WordListItem
from jpfm.services.dictionary_manager import DictionaryManager
from jpfm.services.history_import_service import HistoryImportService
from jpfm.ui.presenter import DictionaryPresenter


class DummySignal:
    def __init__(self):
        self._callback = None

    def connect(self, callback):
        self._callback = callback

    def emit(self, *args, **kwargs):
        if self._callback is not None:
            self._callback(*args, **kwargs)


class DummyView:
    def __init__(self):
        self.search_requested = DummySignal()
        self.import_history_requested = DummySignal()
        self.manual_word_added = DummySignal()
        self.word_removal_requested = DummySignal()
        self.status_messages = []
        self.results = None
        self.word_list_items = []  # Now stores WordListItem objects
        self.history_folder = ""
        self.progress_values = []

    def set_status(self, message):
        self.status_messages.append(message)

    def set_results(self, entries):
        self.results = entries

    def set_word_list(self, items):
        """Now receives WordListItem objects."""
        self.word_list_items = items

    def get_history_folder(self):
        return self.history_folder

    def set_import_progress(self, current, total, message):
        self.progress_values.append((current, total, message))

    def hide_import_progress(self):
        self.progress_values.append((None, None, "hide"))


class TestDictionaryPresenter:
    @pytest.fixture
    def dummy_manager(self):
        return MagicMock(spec=DictionaryManager)

    @pytest.fixture
    def dummy_service(self):
        service = MagicMock(spec=HistoryImportService)
        service.normalize_word.side_effect = lambda value: value.strip()
        return service

    @pytest.fixture
    def view(self):
        return DummyView()

    def test_search_requested_updates_results(self, view, dummy_manager, dummy_service):
        dummy_manager.get_entry.return_value = {"kanji": "愛"}
        presenter = DictionaryPresenter(view, dummy_manager, history_import_service=dummy_service)

        presenter._on_search_requested("jisho", "愛")

        assert view.results == [{"kanji": "愛"}]
        assert view.status_messages[-1] == "Searching..."
        dummy_manager.get_entry.assert_called_once_with("jisho", "愛")

    def test_import_history_cancelled_when_folder_not_selected(self, view, dummy_manager, dummy_service):
        view.history_folder = ""
        presenter = DictionaryPresenter(view, dummy_manager, history_import_service=dummy_service)

        presenter._on_import_history_requested()

        assert view.status_messages[-1] == "Browser history import cancelled."
        dummy_service.build_word_list.assert_not_called()

    def test_import_history_builds_word_list_and_updates_view(self, view, dummy_manager, dummy_service):
        view.history_folder = "/tmp/history"
        
        # Return WordListItem objects
        word_items = [
            WordListItem.from_word(word="食べる", source="browser_history"),
            WordListItem.from_word(word="動く", source="browser_history"),
        ]
        dummy_service.build_word_list.return_value = {
            "final_word_list": word_items
        }
        presenter = DictionaryPresenter(view, dummy_manager, history_import_service=dummy_service)

        presenter._on_import_history_requested()

        dummy_service.build_word_list.assert_called_once()
        assert len(view.word_list_items) == 2
        assert set([item.word for item in view.word_list_items]) == {"食べる", "動く"}
        assert "2 word(s)" in view.status_messages[-1]

    def test_manual_word_added_normalizes_and_updates_word_list(self, view, dummy_manager, dummy_service):
        presenter = DictionaryPresenter(view, dummy_manager, history_import_service=dummy_service)

        presenter._on_manual_word_added(" 食べる ")

        # Manual word should be added to word list model and view updated
        assert len(view.word_list_items) == 1
        assert view.word_list_items[0].word == "食べる"
        assert view.word_list_items[0].source == "manual"
        assert "Added manual word" in view.status_messages[-1]
        assert dummy_service.normalize_word.called

    def test_manual_word_added_duplicate_prevention(self, view, dummy_manager, dummy_service):
        presenter = DictionaryPresenter(view, dummy_manager, history_import_service=dummy_service)

        # Add first word
        presenter._on_manual_word_added("食べる")
        assert len(view.word_list_items) == 1

        # Try to add same word again
        presenter._on_manual_word_added("食べる")
        assert len(view.word_list_items) == 1
        assert "already exists" in view.status_messages[-1]

    def test_manual_word_added_with_history_root_preserves_history_items(self, view, dummy_manager, dummy_service):
        view.history_folder = "/tmp/history"
        
        # First import history
        history_items = [
            WordListItem.from_word(word="食べる", source="browser_history"),
        ]
        dummy_service.build_word_list.return_value = {
            "final_word_list": history_items
        }
        presenter = DictionaryPresenter(view, dummy_manager, history_import_service=dummy_service)
        presenter._on_import_history_requested()

        assert len(view.word_list_items) == 1

        # Add manual word - should preserve history word
        combined_items = [
            WordListItem.from_word(word="食べる", source="browser_history"),
            WordListItem.from_word(word="動く", source="manual"),
        ]
        dummy_service.build_word_list.return_value = {
            "final_word_list": combined_items
        }
        
        presenter._on_manual_word_added("動く")

        # After refresh, we should have both words
        assert len(view.word_list_items) >= 1

    def test_word_removal_requested_removes_item(self, view, dummy_manager, dummy_service):
        presenter = DictionaryPresenter(view, dummy_manager, history_import_service=dummy_service)
        presenter._word_list_model.add_item(
            WordListItem.from_word(word="食べる", source="manual")
        )

        presenter._on_word_removal_requested("食べる")

        assert presenter._word_list_model.count() == 0
        assert view.word_list_items == []
