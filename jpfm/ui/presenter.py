"""Presenter for main UI actions in JPFM.

This module provides `DictionaryPresenter` which wires the passive view
(`MainWindow`) to the service layer (`DictionaryManager`,
`HistoryImportService`) and the `WordListModel`.

It also defines a small background worker used to run batch parsing off
the UI thread and emit progress and finished signals.
"""

from typing import Dict, Any, List, Optional
import threading

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from jpfm.config import update_runtime_config
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
        if hasattr(self._view, "settings_requested"):
            self._view.settings_requested.connect(self._on_settings_requested)
        if hasattr(self._view, "settings_saved"):
            self._view.settings_saved.connect(self._on_settings_saved)

        self._import_service.progress_updated.connect(self._view.set_import_progress)
        self._import_service.import_finished.connect(self._on_import_finished)
        self._import_service.import_error.connect(self._on_import_error)

        # Thread pool for background parsing tasks
        self._thread_pool = QThreadPool.globalInstance()

        # Wire start_parsing UI signal if present
        if hasattr(self._view, "start_parsing"):
            self._view.start_parsing.connect(self._on_start_parsing)
        if hasattr(self._view, "parsed_cache_requested"):
            self._view.parsed_cache_requested.connect(self._on_parsed_cache_requested)

    def _on_parsed_cache_requested(self) -> None:
        """Show a dialog to manage cached parsed entries."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel

        dialog = QDialog(self._view)
        dialog.setWindowTitle("Parsed Cache Manager")
        layout = QVBoxLayout(dialog)

        info = QLabel("Select a source and manage cached parsed words.", dialog)
        layout.addWidget(info)

        # Source selector
        from PySide6.QtWidgets import QComboBox

        source_combo = QComboBox(dialog)
        source_combo.addItems(self._manager.SUPPORTED_SOURCES)
        layout.addWidget(source_combo)

        list_widget = QListWidget(dialog)
        layout.addWidget(list_widget)

        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh", dialog)
        clear_selected_btn = QPushButton("Clear Selected", dialog)
        clear_all_btn = QPushButton("Clear All", dialog)
        close_btn = QPushButton("Close", dialog)

        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(clear_selected_btn)
        btn_layout.addWidget(clear_all_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        def refresh_list():
            list_widget.clear()
            source = source_combo.currentText()
            try:
                words = self._manager.list_cached_words(source)
            except Exception:
                words = []
            for w in words:
                list_widget.addItem(w)

        def clear_selected():
            source = source_combo.currentText()
            items = list_widget.selectedItems()
            for it in items:
                word = it.text()
                try:
                    # remove file via storage clear by deleting specific file
                    # StorageService does not expose single-delete method, so use clear_cache for source then re-save others.
                    # Simpler: delete the file directly
                    from pathlib import Path
                    path = Path(self._manager.storage.cache_dir) / source / f"{word}.json"
                    if path.exists():
                        path.unlink()
                except Exception:
                    pass
            refresh_list()

        def clear_all():
            source = source_combo.currentText()
            try:
                self._manager.clear_cache(source)
            except Exception:
                pass
            refresh_list()

        refresh_btn.clicked.connect(refresh_list)
        clear_selected_btn.clicked.connect(clear_selected)
        clear_all_btn.clicked.connect(clear_all)
        # Refresh list when the source selection changes
        source_combo.currentIndexChanged.connect(lambda _: refresh_list())
        close_btn.clicked.connect(dialog.close)

        # Initial populate
        refresh_list()
        dialog.exec()

    def _on_settings_requested(self) -> None:
        if not hasattr(self._view, "set_settings_values"):
            return
        self._view.set_settings_values(
            pruning_rules=list(self._import_service.pruning_rules),
            learned_words=sorted(self._import_service.learned_words),
        )

    def _on_settings_saved(self, config_data: Dict[str, Any]) -> None:
        updated_config = update_runtime_config(config_data)
        history_import_config = updated_config.get("history_import", {})
        self._import_service.apply_config(history_import_config)
        self._view.set_status("Updated pruning rules and learned words.")

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

    def _on_start_parsing(self) -> None:
        """Begin the parsing workflow for the current word list.

        This runs the batch parsing in a background worker and updates the view
        with progress and final results.
        """
        items = self._word_list_model.get_items()
        if not items:
            self._view.set_status("No words to parse.")
            return

        words = [item.word for item in items]
        source = self._view.source_select.currentText() if hasattr(self._view, "source_select") else "jisho"

        # Prepare UI
        self._view.set_status("Starting parsing...")
        self._view.set_import_progress(0, len(words), "Parsing")

        # Create cancellation token and connect UI cancel to it
        cancel_token = _CancellationToken()
        # Ensure the view button shows 'Cancel' and connect the cancel signal
        self._cancel_connected = False
        self._active_cancel_slot = None
        if hasattr(self._view, "set_parsing_button_state"):
            self._view.set_parsing_button_state(True)
        if hasattr(self._view, "cancel_parsing"):
            # connect and remember the slot so we can disconnect later
            slot = cancel_token.cancel
            self._view.cancel_parsing.connect(slot)
            self._active_cancel_slot = slot
            self._cancel_connected = True

        worker = _ParsingWorker(self._manager, source, words, cancel_token)
        worker.signals.progress.connect(self._view.set_import_progress)
        worker.signals.finished.connect(self._on_parsing_finished)
        self._thread_pool.start(worker)

    def _on_parsing_finished(self, entries: List[Dict[str, Any]]) -> None:
        """Handle parsed results from the background worker."""
        self._view.set_results(entries)
        self._view.hide_import_progress()
        # Reset view button to start state
        if hasattr(self._view, "set_parsing_button_state"):
            self._view.set_parsing_button_state(False)

        # Disconnect cancel signal if we connected it
        if getattr(self, "_cancel_connected", False) and getattr(self, "_active_cancel_slot", None) is not None:
            try:
                if hasattr(self._view, "cancel_parsing"):
                    self._view.cancel_parsing.disconnect(self._active_cancel_slot)
            except Exception:
                # ignore disconnect errors
                pass
            finally:
                self._cancel_connected = False
                self._active_cancel_slot = None

        self._view.set_status(f"Parsing complete: {len(entries)} entries parsed.")


class _WorkerSignals(QObject):
    progress = Signal(int, int, str)
    finished = Signal(list)


class _ParsingWorker(QRunnable):
    """Worker runnable that performs batch parsing off the UI thread.

    Accepts an optional cancellation token which is queried between words.
    """

    def __init__(self, manager: DictionaryManager, source: str, words: List[str], cancel_token: Optional["_CancellationToken"] = None):
        super().__init__()
        self.manager = manager
        self.source = source
        self.words = words
        self.cancel_token = cancel_token
        self.signals = _WorkerSignals()

    def run(self) -> None:  # pragma: no cover - threading behaviour tested via integration
        try:
            def progress_cb(current: int, total: int, word: str) -> None:
                try:
                    self.signals.progress.emit(current, total, f"Parsing: {word}")
                except Exception:
                    pass

            cancel_check = None
            if self.cancel_token is not None:
                cancel_check = self.cancel_token.is_cancelled

            entries = self.manager.batch_get_entries(
                self.source,
                self.words,
                progress_callback=progress_cb,
                cancel_check=cancel_check,
            )
            self.signals.finished.emit(entries)
        except Exception:
            try:
                self.signals.finished.emit([])
            except Exception:
                pass


class _CancellationToken:
    """Thread-safe cancellation token for parsing workers."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()
