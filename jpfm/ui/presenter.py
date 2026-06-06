"""Presenter for main UI actions in JPFM."""

from typing import Dict, Any, List, Optional

from PySide6.QtCore import QObject

from jpfm.services.dictionary_manager import DictionaryManager
from jpfm.services.history_import_service import HistoryImportService
from jpfm.ui.main_window import MainWindow


class DictionaryPresenter(QObject):
    """Presenter that connects the view to the DictionaryManager."""

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
        self._manual_words: List[str] = []
        self._history_root: Optional[str] = None

        self._view.search_requested.connect(self._on_search_requested)
        self._view.import_history_requested.connect(self._on_import_history_requested)
        self._view.manual_word_added.connect(self._on_manual_word_added)

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
        result = self._import_service.build_word_list(history_root, manual_words=self._manual_words)
        self._view.set_word_list(result["final_word_list"])
        self._view.set_status(
            f"Imported {len(result['final_word_list'])} word(s) from history."
        )

    def _on_manual_word_added(self, word: str) -> None:
        normalized = self._import_service.normalize_word(word)
        if not normalized:
            self._view.set_status("Please enter a valid manual word.")
            return

        if normalized not in self._manual_words:
            self._manual_words.append(normalized)

        self._refresh_word_list()

    def _refresh_word_list(self) -> None:
        if self._history_root:
            result = self._import_service.build_word_list(
                self._history_root,
                manual_words=self._manual_words,
            )
            self._view.set_word_list(result["final_word_list"])
            self._view.set_status(
                f"Updated word list ({len(result['final_word_list'])} word(s))."
            )
            return

        self._view.set_word_list(sorted(self._manual_words))
        self._view.set_status(f"Manual words: {len(self._manual_words)} added.")
