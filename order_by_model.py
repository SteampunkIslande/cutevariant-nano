# A simple tablemodel for setting a list of (field name, order) tuple

import PySide6.QtCore as qc
from PySide6.QtCore import Signal

import query as q


class OrderByModel(qc.QAbstractTableModel):

    model_changed = Signal()

    def __init__(self, query: "q.Query", parent=None):
        super().__init__(parent)
        self.query = query
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

    def setData(
        self, index: qc.QModelIndex, value: dict, role=qc.Qt.ItemDataRole.EditRole
    ):
        if role == qc.Qt.ItemDataRole.EditRole:
            if index.row() < 0 or index.row() >= len(self._data):
                return False
            if index.column() < 0 or index.column() >= 2:
                return False
            if "field" in value:
                self._data[index.row()][0] = value["field"]
            if "order" in value:
                self._data[index.row()][1] = value["order"]
            self.dataChanged.emit(index, index)
            self.model_changed.emit()
            return True
        return False

    def removeRow(self, row):
        self.beginRemoveRows(qc.QModelIndex(), row, row)
        self._data.pop(row)
        self.endRemoveRows()
        self.model_changed.emit

    def add_order_by(self, field, order):
        self.beginInsertRows(qc.QModelIndex(), len(self._data), len(self._data))
        self._data.append([field, order])
        self.endInsertRows()
        self.model_changed.emit()

    def load(self, data):
        self.beginResetModel()
        self._data = data
        self.endResetModel()
        self.model_changed.emit()

    def get_data(self):
        return self._data

    def flags(self, index: qc.QModelIndex):
        return (
            qc.Qt.ItemFlag.ItemIsEditable
            | qc.Qt.ItemFlag.ItemIsEnabled
            | qc.Qt.ItemFlag.ItemIsDragEnabled
            | qc.Qt.ItemFlag.ItemIsDropEnabled
            | qc.Qt.ItemFlag.ItemIsSelectable
        )
