"""Unit tests for JPFM main window UI components."""

from PySide6.QtCore import Qt

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


def test_set_word_list_updates_list_widget(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.set_word_list(["食べる", "動く"])

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
    dummy_service.build_word_list.return_value = {"final_word_list": ["食べる"]}

    presenter = DictionaryPresenter(window, dummy_manager, history_import_service=dummy_service)

    window.manual_word_input.setText("食べる")
    window.manual_add_button.click()

    assert window.word_list_widget.count() == 1
    assert window.word_list_widget.item(0).text() == "食べる"
    assert window.status_label.text() == "Manual words: 1 added."
