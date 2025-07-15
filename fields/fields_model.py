# A model to selected fields using checkboxes


import logging

import PySide6.QtCore as qc

LOGGER = logging.getLogger(__name__)


class FieldsModel(qc.QAbstractItemModel):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.fields = []

    def update_fields(self, fields: list[str]):
        self.load(fields)

    def load(self, fields: list[str]):
        self.beginResetModel()
        if not fields:
            self.fields = []
            self.endResetModel()
            return
        self.fields = [(f, qc.Qt.CheckState.Unchecked) for f in fields]
        self.endResetModel()

    def canDropMimeData(self, data, action, row, column, parent):
        """Check if the drop is allowed."""
        if parent.isValid():
            return False
        return True

    def rowCount(self, parent=qc.QModelIndex()):
        """Return the number of rows in the model."""
        if parent.isValid():
            return 0
        return len(self.fields)

    def columnCount(self, parent=qc.QModelIndex()):
        """Return the number of columns in the model."""
        return 1

    def data(self, index, role=qc.Qt.ItemDataRole.DisplayRole):
        """Return the data for the given index and role."""
        if not index.isValid() or index.row() < 0 or index.row() >= len(self.fields):
            return None

        field, checkstate = self.fields[index.row()]

        if role == qc.Qt.ItemDataRole.DisplayRole:
            return field
        elif role == qc.Qt.ItemDataRole.CheckStateRole:
            return checkstate

        return None

    def setData(self, index, value, role=qc.Qt.ItemDataRole.EditRole):
        """Set the data for the given index and role."""
        if not index.isValid() or index.row() < 0 or index.row() >= len(self.fields):
            return False

        if role == qc.Qt.ItemDataRole.CheckStateRole:
            self.fields[index.row()] = (
                self.fields[index.row()][0],
                value,
            )
            self.dataChanged.emit(index, index)
            return True

        return False

    def parent(self, index: qc.QModelIndex):
        """Return the parent index for the given index."""
        if not index.isValid() or index.row() < 0 or index.row() >= len(self.fields):
            return qc.QModelIndex()
        return qc.QModelIndex()

    def index(self, row, column, parent=qc.QModelIndex()):
        """Return the index for the given row and column."""
        if parent.isValid() or row < 0 or row >= len(self.fields) or column != 0:
            return qc.QModelIndex()
        return self.createIndex(row, column, None)

    def flags(self, index):
        if not index.isValid() or index.row() < 0 or index.row() >= len(self.fields):
            return super().flags(index)
        return (
            qc.Qt.ItemFlag.ItemIsEnabled
            | qc.Qt.ItemFlag.ItemIsSelectable
            | qc.Qt.ItemFlag.ItemIsUserCheckable
        )

    def set_checked_fields(self, fields: list[str]):
        self.beginResetModel()
        for i, (field, _) in enumerate(self.fields):
            if field in fields or len(fields) == 0:
                self.fields[i] = (field, qc.Qt.CheckState.Checked)
            else:
                self.fields[i] = (field, qc.Qt.CheckState.Unchecked)
        self.endResetModel()

    def checked_fields(self):
        return [
            field
            for field, checkstate in self.fields
            if checkstate == qc.Qt.CheckState.Checked
        ]

    def get_all_fields(self):
        return [f[0] for f in self.fields]

    def __del__(self):
        LOGGER.debug("FieldsModel deleted")
