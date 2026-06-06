"""Main application window for JPFM."""

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
)

from jpfm.config import GUI_WINDOW_HEIGHT, GUI_WINDOW_WIDTH
from jpfm.ui.entry_table_model import EntryTableModel


class MainWindow(QMainWindow):
    """Passive view for the JPFM main UI."""

    search_requested = Signal(str, str)

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

        self.source_select = QComboBox(self)
        self.source_select.addItems(self.sources)
        self.source_select.setObjectName("source_select")

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Enter a Japanese word or kanji")
        self.search_input.setObjectName("search_input")

        self.search_button = QPushButton("Search", self)
        self.search_button.setObjectName("search_button")

        controls_layout.addWidget(self.source_select)
        controls_layout.addWidget(self.search_input)
        controls_layout.addWidget(self.search_button)

        self.status_label = QLabel("Ready", self)
        self.status_label.setObjectName("status_label")

        self.results_model = EntryTableModel([])
        self.results_view = QTableView(self)
        self.results_view.setModel(self.results_model)
        self.results_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.results_view.horizontalHeader().setStretchLastSection(True)
        self.results_view.setObjectName("results_view")

        layout.addLayout(controls_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.results_view)

        self.search_button.clicked.connect(self._on_search_clicked)
        self.search_input.returnPressed.connect(self._on_search_clicked)

    def _on_search_clicked(self) -> None:
        word = self.search_input.text().strip()
        source = self.source_select.currentText()
        if not word:
            self.set_status("Please enter a search term.")
            return

        self.search_requested.emit(source, word)

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
