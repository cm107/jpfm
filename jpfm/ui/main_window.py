"""Main application window for JPFM."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPushButton,
    QProgressBar,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from jpfm.config import GUI_WINDOW_HEIGHT, GUI_WINDOW_WIDTH
from jpfm.models.word_list_item import WordListItem
from jpfm.ui.entry_table_model import EntryTableModel


class MainWindow(QMainWindow):
    """Passive view for the JPFM main UI."""

    search_requested = Signal(str, str)
    parsed_cache_requested = Signal()
    import_history_requested = Signal()
    start_parsing = Signal()
    cancel_parsing = Signal()
    manual_word_added = Signal(str)
    word_removal_requested = Signal(str)
    settings_requested = Signal()
    settings_saved = Signal(dict)

    def __init__(
        self,
        sources: Optional[List[str]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.sources = sources or ["jisho", "kotobank", "koohii"]
        self.setWindowTitle("JPFM Dictionary")
        self.resize(GUI_WINDOW_WIDTH, GUI_WINDOW_HEIGHT)

        self._current_pruning_rules: List[Dict[str, Any]] = []
        self._current_learned_words: List[str] = []
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

        self.settings_button = QPushButton("Settings", self)
        self.settings_button.setObjectName("settings_button")

        self.start_parsing_button = QPushButton("Start Parsing", self)
        self.start_parsing_button.setObjectName("start_parsing_button")
        self._parsing_active = False

        controls_layout.addWidget(self.source_select)
        controls_layout.addWidget(self.search_input)
        controls_layout.addWidget(self.search_button)
        controls_layout.addWidget(self.import_history_button)
        controls_layout.addWidget(self.settings_button)
        controls_layout.addWidget(self.start_parsing_button)

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
        # Menu bar with File -> Parsed Cache
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        parsed_cache_action = file_menu.addAction("Parsed Cache")
        parsed_cache_action.triggered.connect(lambda: self.parsed_cache_requested.emit())
        layout.addLayout(import_layout)
        layout.addWidget(QLabel("Word List", self))
        layout.addWidget(self.word_list_widget)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.results_view)

        self.search_button.clicked.connect(self._on_search_clicked)
        self.search_input.returnPressed.connect(self._on_search_clicked)
        self.import_history_button.clicked.connect(self._on_import_history_clicked)
        self.settings_button.clicked.connect(self._on_settings_clicked)
        self.start_parsing_button.clicked.connect(self._on_start_parsing_clicked)
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

    def _on_settings_clicked(self) -> None:
        self.settings_requested.emit()
        self._show_settings_dialog()

    def _on_start_parsing_clicked(self) -> None:
        """Toggle the parsing session between starting and cancelling."""
        if not getattr(self, "_parsing_active", False):
            self.set_parsing_button_state(True)
            self.start_parsing.emit()
            self.set_import_progress(0, 0, "Starting parsing...")
            return

        self.cancel_parsing.emit()
        self.set_parsing_button_state(False)

    def set_parsing_button_state(self, active: bool) -> None:
        """Set the start/cancel button state.

        When `active` is True the button shows 'Cancel'; otherwise 'Start Parsing'.
        """
        self._parsing_active = bool(active)
        self.start_parsing_button.setText("Cancel" if self._parsing_active else "Start Parsing")

    def _show_settings_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("User Settings")
        dialog_layout = QVBoxLayout(dialog)

        pruning_label = QLabel("Pruning rules", dialog)
        self.pruning_rule_type_combo = QComboBox(dialog)
        self.pruning_rule_type_combo.addItems(
            ["prohibited_characters", "prohibited_strings", "regex"]
        )
        self.pruning_rule_value_input = QLineEdit(dialog)
        self.pruning_rule_value_input.setPlaceholderText("Rule value")
        self.pruning_rule_add_button = QPushButton("Add Rule", dialog)
        self.pruning_rule_remove_button = QPushButton("Remove Rule", dialog)
        self.pruning_rules_list = QListWidget(dialog)

        learned_label = QLabel("Learned words", dialog)
        self.learned_word_input = QLineEdit(dialog)
        self.learned_word_input.setPlaceholderText("食べる")
        self.learned_word_add_button = QPushButton("Add Word", dialog)
        self.learned_word_remove_button = QPushButton("Remove Word", dialog)
        self.learned_words_list = QListWidget(dialog)

        pruning_entry_layout = QHBoxLayout()
        pruning_entry_layout.addWidget(self.pruning_rule_type_combo)
        pruning_entry_layout.addWidget(self.pruning_rule_value_input)
        pruning_entry_layout.addWidget(self.pruning_rule_add_button)
        pruning_entry_layout.addWidget(self.pruning_rule_remove_button)

        learned_entry_layout = QHBoxLayout()
        learned_entry_layout.addWidget(self.learned_word_input)
        learned_entry_layout.addWidget(self.learned_word_add_button)
        learned_entry_layout.addWidget(self.learned_word_remove_button)

        dialog_layout.addWidget(pruning_label)
        dialog_layout.addLayout(pruning_entry_layout)
        dialog_layout.addWidget(self.pruning_rules_list)
        dialog_layout.addWidget(learned_label)
        dialog_layout.addLayout(learned_entry_layout)
        dialog_layout.addWidget(self.learned_words_list)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(lambda: self._save_settings(dialog))
        buttons.rejected.connect(dialog.reject)
        dialog_layout.addWidget(buttons)

        self.pruning_rule_add_button.clicked.connect(self._add_pruning_rule)
        self.pruning_rule_remove_button.clicked.connect(self._remove_pruning_rule)
        self.learned_word_add_button.clicked.connect(self._add_learned_word)
        self.learned_word_remove_button.clicked.connect(self._remove_learned_word)

        self._populate_settings_editors()
        dialog.show()

    def _populate_settings_editors(self) -> None:
        if not hasattr(self, "pruning_rules_list") or not hasattr(self, "learned_words_list"):
            return

        self.pruning_rules_list.clear()
        for rule in self._current_pruning_rules or []:
            rule_type = rule.get("type", "")
            rule_value = rule.get("value", "")
            self.pruning_rules_list.addItem(f"{rule_type}: {rule_value}")

        self.learned_words_list.clear()
        for word in self._current_learned_words or []:
            self.learned_words_list.addItem(word)

    def _add_pruning_rule(self) -> None:
        rule_type = self.pruning_rule_type_combo.currentText().strip()
        rule_value = self.pruning_rule_value_input.text().strip()
        if not rule_value:
            self.set_status("Please enter a pruning rule value.")
            return

        self.pruning_rules_list.addItem(f"{rule_type}: {rule_value}")
        self.pruning_rule_value_input.clear()

    def _remove_pruning_rule(self) -> None:
        selected_items = self.pruning_rules_list.selectedItems()
        for item in selected_items:
            self.pruning_rules_list.takeItem(self.pruning_rules_list.row(item))

    def _add_learned_word(self) -> None:
        word = self.learned_word_input.text().strip()
        if not word:
            self.set_status("Please enter a learned word.")
            return

        self.learned_words_list.addItem(word)
        self.learned_word_input.clear()

    def _remove_learned_word(self) -> None:
        selected_items = self.learned_words_list.selectedItems()
        for item in selected_items:
            self.learned_words_list.takeItem(self.learned_words_list.row(item))

    def _collect_pruning_rules(self) -> List[Dict[str, Any]]:
        pruning_rules: List[Dict[str, Any]] = []
        for index in range(self.pruning_rules_list.count()):
            text = self.pruning_rules_list.item(index).text()
            if ":" not in text:
                continue
            rule_type, rule_value = text.split(":", 1)
            pruning_rules.append({"type": rule_type.strip(), "value": rule_value.strip()})
        return pruning_rules

    def _collect_learned_words(self) -> List[str]:
        learned_words: List[str] = []
        for index in range(self.learned_words_list.count()):
            learned_words.append(self.learned_words_list.item(index).text().strip())
        return learned_words

    def _save_settings(self, dialog: Optional[QDialog] = None) -> None:
        pruning_rules = self._collect_pruning_rules()
        learned_words = self._collect_learned_words()

        self.settings_saved.emit(
            {
                "history_import": {
                    "pruning_rules": pruning_rules,
                    "learned_words": learned_words,
                }
            }
        )
        if dialog is not None:
            dialog.accept()

    def set_settings_values(self, pruning_rules: Optional[List[Dict[str, Any]]] = None, learned_words: Optional[List[str]] = None) -> None:
        """Populate the settings dialog fields with the current configuration values."""
        self._current_pruning_rules = pruning_rules or []
        self._current_learned_words = learned_words or []

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
