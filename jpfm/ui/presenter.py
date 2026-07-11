"""Presenter for main UI actions in JPFM."""

from typing import Dict, Any, List, Optional

from PySide6.QtCore import QObject

from jpfm.models.word_list_item import WordListItem
from jpfm.services.dictionary_manager import DictionaryManager
from jpfm.services.history_import_service import HistoryImportService
from jpfm.services.word_list_model import WordListModel
from jpfm.ui.main_window import MainWindow


class DictionaryPresenter(QObject):
    """Presenter that connects the view to the DictionaryManager and WordListModel."""

    def __init__(
        self,
        view: MainWindow,
        manager: DictionaryManager,
        history_import_service: Optional[HistoryImportService] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._view = view
        self._manager = manager
        self._import_service = history_import_service or HistoryImportService()
        self._word_list_model = WordListModel(parent=self)
        self._history_root: Optional[str] = None

        # Connect word list model signals to view updates
        self._word_list_model.items_changed.connect(self._on_word_list_changed)

        # Connect view signals to presenter handlers
        self._view.search_requested.connect(self._on_search_requested)
        self._view.import_history_requested.connect(self._on_import_history_requested)
        self._view.manual_word_added.connect(self._on_manual_word_added)
        self._view.word_removal_requested.connect(self._on_word_removal_requested)

        self._import_service.progress_updated.connect(self._view.set_import_progress)
        self._import_service.import_finished.connect(self._on_import_finished)
        self._import_service.import_error.connect(self._on_import_error)

    def _on_search_requested(self, source: str, word: str) -> None:
        self._view.set_status("Searching...")
        entry = self._manager.get_entry(source, word)
        entries: List[Dict[str, Any]] = [entry] if entry is not None else []
        self._view.set_results(entries)

    def _on_import_history_requested(self) -> None:
        history_root = self._view.get_history_folder()
        if not history_root:
            self._view.set_status("Browser history import cancelled.")
            return

        self._history_root = history_root
        self._view.set_status("Importing history words...")
        result = self._import_service.build_word_list(
            history_root,
            manual_words=[item.word for item in self._word_list_model.get_items() if item.source == "manual"],
        )
        self._on_import_finished(result)

    def _on_manual_word_added(self, word: str) -> None:
        normalized = self._import_service.normalize_word(word)
        if not normalized:
            self._view.set_status("Please enter a valid manual word.")
            return

        # Check if word already exists
        if self._word_list_model.get_by_word(normalized) is not None:
            self._view.set_status(f"Word '{normalized}' already exists in list.")
            return

        # Create new WordListItem for manual word
        item = WordListItem.from_word(
            word=normalized,
            source="manual",
        )
        self._word_list_model.add_item(item)
        self._view.set_status(f"Added manual word: {normalized}")

    def _refresh_word_list(self) -> None:
        """Refresh word list display from model.
        
        If history root is set, rebuild from history + manual words.
        Otherwise, just display the current manual words.
        """
        if self._history_root:
            result = self._import_service.build_word_list(
                self._history_root,
                manual_words=[item.word for item in self._word_list_model.get_items() if item.source == "manual"],
            )
            self._on_import_finished(result)
            return

        # Just display manual words
        manual_items = [item for item in self._word_list_model.get_items() if item.source == "manual"]
        self._word_list_model.clear()
        self._word_list_model.add_items(manual_items)

    def _on_import_finished(self, result: Dict[str, Any]) -> None:
        """Apply completed import results to the word list model."""
        final_items: List[WordListItem] = result["final_word_list"]
        self._word_list_model.clear()
        self._word_list_model.add_items(final_items)
        self._view.hide_import_progress()
        self._view.set_status(
            f"Imported {self._word_list_model.count()} word(s) from history."
        )

    def _on_import_error(self, message: str) -> None:
        """Handle history import errors."""
        self._view.hide_import_progress()
        self._view.set_status(message)

    def _on_word_removal_requested(self, word: str) -> None:
        """Remove a word from the current word list."""
        try:
            self._word_list_model.remove_item(word)
        except ValueError:
            self._view.set_status(f"Word '{word}' not found.")
            return

        self._view.set_status(f"Removed word: {word}")

    def _on_word_list_changed(self) -> None:
        """Handle word list model changes and update view."""
        items = self._word_list_model.get_items()
        self._view.set_word_list(items)
        self._view.set_status(f"Word list updated: {len(items)} word(s).")
