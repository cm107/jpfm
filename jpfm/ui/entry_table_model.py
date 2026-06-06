"""Model definitions for dictionary result display."""

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex


class EntryTableModel(QAbstractTableModel):
    """A table model for parsed dictionary entries."""

    def __init__(
        self,
        entries: Optional[List[Dict[str, Any]]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._headers = ["Kanji", "Reading", "Definitions"]
        self._fields = ["kanji", "reading", "definitions"]
        self._entries = entries or []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._entries)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Optional[str]:
        if not index.isValid() or role != Qt.DisplayRole:
            return None

        entry = self._entries[index.row()]
        field = self._fields[index.column()]
        value = entry.get(field, "")

        if isinstance(value, list):
            return "; ".join(str(item) for item in value)

        return str(value) if value is not None else ""

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.DisplayRole,
    ) -> Optional[str]:
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            return self._headers[section]

        if orientation == Qt.Vertical:
            return str(section + 1)

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def hasChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
        if not parent.isValid():
            return self.rowCount(parent) > 0
        return False

    def parent(self, index: QModelIndex) -> QModelIndex:
        return QModelIndex()

    def set_entries(self, entries: List[Dict[str, Any]]) -> None:
        self.beginResetModel()
        self._entries = entries or []
        self.endResetModel()
