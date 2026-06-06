"""Presenter for main UI actions in JPFM."""

from typing import Dict, Any, List

from PySide6.QtCore import QObject

from jpfm.services.dictionary_manager import DictionaryManager
from jpfm.ui.main_window import MainWindow


class DictionaryPresenter(QObject):
    """Presenter that connects the view to the DictionaryManager."""

    def __init__(self, view: MainWindow, manager: DictionaryManager, parent=None) -> None:
        super().__init__(parent)
        self._view = view
        self._manager = manager
        self._view.search_requested.connect(self._on_search_requested)

    def _on_search_requested(self, source: str, word: str) -> None:
        self._view.set_status("Searching...")
        entry = self._manager.get_entry(source, word)
        entries: List[Dict[str, Any]] = [entry] if entry is not None else []
        self._view.set_results(entries)
