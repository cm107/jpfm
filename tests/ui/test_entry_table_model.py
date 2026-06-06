"""Unit tests for the JPFM entry table model."""

from jpfm.ui.entry_table_model import EntryTableModel


def test_entry_table_model_structure(qtmodeltester):
    entries = [
        {"kanji": "愛", "reading": "あい", "definitions": ["love", "affection"]},
        {"kanji": "行", "reading": "い", "definitions": ["go"]},
    ]

    model = EntryTableModel(entries)
    qtmodeltester.check(model, force_py=True)

    assert model.rowCount() == 2
    assert model.columnCount() == 3
    assert model.data(model.index(0, 0)) == "愛"
    assert model.data(model.index(0, 2)) == "love; affection"


from PySide6.QtCore import Qt


def test_entry_table_model_header_data():
    model = EntryTableModel([])

    assert model.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "Kanji"
    assert model.headerData(1, Qt.Horizontal, Qt.DisplayRole) == "Reading"
    assert model.headerData(2, Qt.Horizontal, Qt.DisplayRole) == "Definitions"
