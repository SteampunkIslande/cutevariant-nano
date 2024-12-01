# A simple tablemodel for setting a list of (field name, order) tuple

import PySide6.QtCore as qc
from PySide6.QtCore import Signal


class OrderByModel(qc.QAbstractTableModel):

    model_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self._data)

    def columnCount(self, parent):
        if parent.isValid():
            return 0
        return 2

    def data(self, index: qc.QModelIndex, role=qc.Qt.ItemDataRole.DisplayRole):
        if role == qc.Qt.ItemDataRole.DisplayRole:
            if index.row() < 0 or index.row() >= len(self._data):
                return None
            if index.column() < 0 or index.column() >= 2:
                return None
            return self._data[index.row()][index.column()]
        return None

    def setData(self, index: qc.QModelIndex, value, role=qc.Qt.ItemDataRole.EditRole):
        if role == qc.Qt.ItemDataRole.EditRole:
            if index.row() < 0 or index.row() >= len(self._data):
                return False
            if index.column() < 0 or index.column() >= 2:
                return False
            self._data[index.row()][index.column()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def get_data(self):
        return self._data

    def flags(self, index: qc.QModelIndex):
        return (
            qc.Qt.ItemFlag.ItemIsEditable
            | qc.Qt.ItemFlag.ItemIsEnabled
            | qc.Qt.ItemFlag.ItemIsDragEnabled
            | qc.Qt.ItemFlag.ItemIsDropEnabled
        )
