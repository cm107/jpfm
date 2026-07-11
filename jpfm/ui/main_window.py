"""Main application window for JPFM."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QProgressBar,
    QTableView,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
    QListWidget,
)

from jpfm.config import GUI_WINDOW_HEIGHT, GUI_WINDOW_WIDTH
from jpfm.models.word_list_item import WordListItem
from jpfm.ui.entry_table_model import EntryTableModel


class MainWindow(QMainWindow):
    """Passive view for the JPFM main UI."""

    search_requested = Signal(str, str)
    import_history_requested = Signal()
    manual_word_added = Signal(str)
    word_removal_requested = Signal(str)

    def __init__(
        self,
        sources: Optional[List[str]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.sources = sources or ["jisho", "kotobank", "koohii"]
        self.setWindowTitle("JPFM Dictionary")
        self.resize(GUI_WINDOW_WIDTH, GUI_WINDOW_HEIGHT)

        self._setup_ui()

    def _setup_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        controls_layout = QHBoxLayout()
        import_layout = QHBoxLayout()

        self.source_select = QComboBox(self)
        self.source_select.addItems(self.sources)
        self.source_select.setObjectName("source_select")

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Enter a Japanese word or kanji")
        self.search_input.setObjectName("search_input")

        self.search_button = QPushButton("Search", self)
        self.search_button.setObjectName("search_button")

        self.import_history_button = QPushButton("Import History", self)
        self.import_history_button.setObjectName("import_history_button")

        controls_layout.addWidget(self.source_select)
        controls_layout.addWidget(self.search_input)
        controls_layout.addWidget(self.search_button)
        controls_layout.addWidget(self.import_history_button)

        self.manual_word_input = QLineEdit(self)
        self.manual_word_input.setPlaceholderText("Add manual word")
        self.manual_word_input.setObjectName("manual_word_input")

        self.manual_add_button = QPushButton("Add", self)
        self.manual_add_button.setObjectName("manual_add_button")

        self.remove_word_button = QPushButton("Remove Selected", self)
        self.remove_word_button.setObjectName("remove_word_button")

        import_layout.addWidget(self.manual_word_input)
        import_layout.addWidget(self.manual_add_button)
        import_layout.addWidget(self.remove_word_button)

        self.status_label = QLabel("Ready", self)
        self.status_label.setObjectName("status_label")

        self.word_list_widget = QListWidget(self)
        self.word_list_widget.setObjectName("word_list_widget")

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setObjectName("import_progress_bar")
        self.progress_bar.setVisible(False)

        self.results_model = EntryTableModel([])
        self.results_view = QTableView(self)
        self.results_view.setModel(self.results_model)
        self.results_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.results_view.horizontalHeader().setStretchLastSection(True)
        self.results_view.setObjectName("results_view")

        layout.addLayout(controls_layout)
        layout.addLayout(import_layout)
        layout.addWidget(QLabel("Word List", self))
        layout.addWidget(self.word_list_widget)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.results_view)

        self.search_button.clicked.connect(self._on_search_clicked)
        self.search_input.returnPressed.connect(self._on_search_clicked)
        self.import_history_button.clicked.connect(self._on_import_history_clicked)
        self.manual_add_button.clicked.connect(self._on_manual_add_clicked)
        self.remove_word_button.clicked.connect(self._on_remove_word_clicked)
        self.manual_word_input.returnPressed.connect(self._on_manual_add_clicked)

    def _on_search_clicked(self) -> None:
        word = self.search_input.text().strip()
        source = self.source_select.currentText()
        if not word:
            self.set_status("Please enter a search term.")
            return

        self.search_requested.emit(source, word)

    def _on_import_history_clicked(self) -> None:
        self.import_history_requested.emit()

    def _on_manual_add_clicked(self) -> None:
        word = self.manual_word_input.text().strip()
        if not word:
            self.set_status("Please enter a manual word.")
            return

        self.manual_word_added.emit(word)
        self.manual_word_input.clear()

    def _on_remove_word_clicked(self) -> None:
        selected_items = self.word_list_widget.selectedItems()
        if not selected_items:
            self.set_status("Please select a word to remove.")
            return

        word = selected_items[0].text()
        self.word_removal_requested.emit(word)

    def get_history_folder(self) -> str:
        return QFileDialog.getExistingDirectory(
            self,
            "Select Browser History Root",
            str(Path.home()),
        )

    def set_word_list(self, items: List[WordListItem]) -> None:
        """Set the word list display from a list of WordListItem objects.
        
        Args:
            items: List of WordListItem to display.
        """
        self.word_list_widget.clear()
        for item in items:
            self.word_list_widget.addItem(item.word)

    def set_import_progress(self, current: Optional[int], total: Optional[int], message: str) -> None:
        """Show or update the import progress bar."""
        if total is None or total <= 0:
            self.progress_bar.setVisible(False)
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current or 0)
        self.progress_bar.setFormat(f"{message} ({current}/{total})")

    def hide_import_progress(self) -> None:
        """Hide the import progress bar."""
        self.progress_bar.setVisible(False)

    def set_results(self, entries: List[Dict[str, Any]]) -> None:
        self.results_model.set_entries(entries)
        if entries:
            self.set_status(f"Found {len(entries)} result(s)")
        else:
            self.set_status("No results found")

    def clear_results(self) -> None:
        self.results_model.set_entries([])

    def set_status(self, message: str) -> None:
        self.status_label.setText(message)
