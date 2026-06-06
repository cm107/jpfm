"""Unit tests for JPFM main window UI components."""

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
