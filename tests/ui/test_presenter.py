"""
Unit tests for the DictionaryPresenter.

These tests verify that the presenter correctly coordinates the view, dictionary
manager, and history import service for search, history import, and manual word entry.
"""

from unittest.mock import MagicMock

import pytest

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
        self.status_messages = []
        self.results = None
        self.word_list = []
        self.history_folder = ""

    def set_status(self, message):
        self.status_messages.append(message)

    def set_results(self, entries):
        self.results = entries

    def set_word_list(self, words):
        self.word_list = words

    def get_history_folder(self):
        return self.history_folder


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
        dummy_service.build_word_list.return_value = {
            "final_word_list": ["食べる", "動く"]
        }
        presenter = DictionaryPresenter(view, dummy_manager, history_import_service=dummy_service)

        presenter._on_import_history_requested()

        dummy_service.build_word_list.assert_called_once_with("/tmp/history", manual_words=[])
        assert view.word_list == ["食べる", "動く"]
        assert view.status_messages[-1] == "Imported 2 word(s) from history."

    def test_manual_word_added_normalizes_and_refreshes_word_list(self, view, dummy_manager, dummy_service):
        dummy_service.build_word_list.return_value = {
            "final_word_list": ["食べる", "動く"]
        }
        presenter = DictionaryPresenter(view, dummy_manager, history_import_service=dummy_service)

        presenter._on_manual_word_added(" 食べる ")

        assert view.word_list == ["食べる"]
        assert view.status_messages[-1] == "Manual words: 1 added."
        assert dummy_service.normalize_word.call_args.args[0] == " 食べる "

    def test_manual_word_added_with_history_root_rebuilds_word_list(self, view, dummy_manager, dummy_service):
        view.history_folder = "/tmp/history"
        dummy_service.build_word_list.side_effect = [
            {"final_word_list": ["食べる"]},
            {"final_word_list": ["食べる", "動く"]},
        ]
        presenter = DictionaryPresenter(view, dummy_manager, history_import_service=dummy_service)

        presenter._on_import_history_requested()
        presenter._on_manual_word_added("動く")

        assert view.word_list == ["食べる", "動く"]
        assert view.status_messages[-1] == "Updated word list (2 word(s))."
        assert dummy_service.build_word_list.call_count == 2
