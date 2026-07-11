"""Unit tests for JPFM main window UI components."""

from PySide6.QtCore import Qt

from jpfm.models.word_list_item import WordListItem
from jpfm.ui.main_window import MainWindow


def test_search_button_emits_search_requested(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.search_input.setText("愛")
    window.source_select.setCurrentText("jisho")

    with qtbot.waitSignal(window.search_requested, timeout=1000) as signal:
        window.search_button.click()

    assert signal.args == ["jisho", "愛"]


def test_return_key_emits_search_requested(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.search_input.setText("音")
    window.source_select.setCurrentText("kotobank")

    with qtbot.waitSignal(window.search_requested, timeout=1000) as signal:
        window.search_input.returnPressed.emit()

    assert signal.args == ["kotobank", "音"]


def test_set_results_updates_model_and_status(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.set_results([
        {"kanji": "愛", "reading": "あい", "definitions": ["love"]}
    ])

    assert window.results_view.model().rowCount() == 1
    assert window.status_label.text() == "Found 1 result(s)"


def test_import_history_button_emits_import_history_requested(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    with qtbot.waitSignal(window.import_history_requested, timeout=1000) as signal:
        window.import_history_button.click()

    assert signal.args == []


def test_manual_add_button_emits_manual_word_added(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.manual_word_input.setText("食べる")
    with qtbot.waitSignal(window.manual_word_added, timeout=1000) as signal:
        window.manual_add_button.click()

    assert signal.args == ["食べる"]


def test_settings_button_emits_settings_requested(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    with qtbot.waitSignal(window.settings_requested, timeout=1000) as signal:
        window.settings_button.click()

    assert signal.args == []


def test_settings_dialog_manages_pruning_rules(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_settings_values(pruning_rules=[{"type": "prohibited_characters", "value": "*"}], learned_words=[])
    window._show_settings_dialog()

    window.pruning_rule_value_input.setText("#")
    window._add_pruning_rule()
    assert window.pruning_rules_list.count() == 2
    assert window.pruning_rules_list.item(1).text() == "prohibited_characters: #"

    window.pruning_rules_list.setCurrentRow(0)
    window._remove_pruning_rule()
    assert window.pruning_rules_list.count() == 1

    with qtbot.waitSignal(window.settings_saved, timeout=1000) as signal:
        window._save_settings(None)

    saved_config = signal.args[0]
    assert saved_config["history_import"]["pruning_rules"] == [{"type": "prohibited_characters", "value": "#"}]


def test_settings_dialog_manages_learned_words(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_settings_values(pruning_rules=[], learned_words=["食べる"])
    window._show_settings_dialog()

    window.learned_word_input.setText("動く")
    window._add_learned_word()
    assert window.learned_words_list.count() == 2
    assert window.learned_words_list.item(1).text() == "動く"

    window.learned_words_list.setCurrentRow(0)
    window._remove_learned_word()
    assert window.learned_words_list.count() == 1

    with qtbot.waitSignal(window.settings_saved, timeout=1000) as signal:
        window._save_settings(None)

    saved_config = signal.args[0]
    assert saved_config["history_import"]["learned_words"] == ["動く"]


def test_set_word_list_updates_list_widget(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    items = [
        WordListItem.from_word(word="食べる"),
        WordListItem.from_word(word="動く"),
    ]
    window.set_word_list(items)

    assert window.word_list_widget.count() == 2
    assert window.word_list_widget.item(0).text() == "食べる"
    assert window.status_label.text() == "Ready"


def test_manual_add_button_updates_word_list_with_presenter(qtbot):
    from unittest.mock import MagicMock

    from jpfm.services.dictionary_manager import DictionaryManager
    from jpfm.services.history_import_service import HistoryImportService
    from jpfm.ui.presenter import DictionaryPresenter

    window = MainWindow()
    qtbot.addWidget(window)

    dummy_manager = MagicMock(spec=DictionaryManager)
    dummy_service = MagicMock(spec=HistoryImportService)
    dummy_service.normalize_word.side_effect = lambda value: value.strip()
    
    word_items = [WordListItem.from_word(word="食べる", source="manual")]
    dummy_service.build_word_list.return_value = {"final_word_list": word_items}

    presenter = DictionaryPresenter(window, dummy_manager, history_import_service=dummy_service)

    window.manual_word_input.setText("食べる")
    window.manual_add_button.click()

    assert window.word_list_widget.count() == 1
    assert window.word_list_widget.item(0).text() == "食べる"
    # Status message changed with new presenter logic
    assert "Added manual word" in window.status_label.text()
