# A model to selected fields using checkboxes


import json
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

    def supportedDropActions(self):
        """Return the drop actions supported by this model."""
        return qc.Qt.DropAction.MoveAction

    def mimeTypes(self):
        """Return the list of MIME types supported by this model."""
        return ["text/json"]

    def mimeData(self, indexes):
        """Create MIME data for the given indexes."""
        mime_data = qc.QMimeData()
        if not indexes:
            return mime_data

        if len(indexes) != 1:
            return mime_data

        data = {
            "field_index": indexes[0].row(),
        }

        mime_data.setData("text/json", json.dumps(data).encode("utf-8"))

        return mime_data

    def canDropMimeData(
        self,
        data: qc.QMimeData,
        action: qc.Qt.DropAction,
        row: int,
        column: int,
        parent: qc.QModelIndex,
    ):
        """Check if the drop is allowed."""
        if (
            not parent.isValid()
            and action == qc.Qt.DropAction.MoveAction
            and data.hasFormat("text/json")
        ):
            return True
        return False

    def dropMimeData(self, data, action, row, column, parent):
        """Handle the drop of MIME data."""
        if not self.canDropMimeData(data, action, row, column, parent):
            return False

        if action == qc.Qt.DropAction.IgnoreAction:
            return True

        if not data.hasFormat("text/json"):
            LOGGER.warning("Drop data does not have the expected format.")
            return False

        try:
            json_data: dict = json.loads(data.data("text/json").data().decode("utf-8"))
        except json.JSONDecodeError:
            LOGGER.error("Failed to decode JSON data from drop.")
            return False

        field_index = json_data.get("field_index")

        self.beginMoveRows(
            qc.QModelIndex(), field_index, field_index, qc.QModelIndex(), row - 1
        )
        self.fields.insert(row, self.fields.pop(field_index))
        self.endMoveRows()

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
                qc.Qt.CheckState(value),
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
            return qc.Qt.ItemFlag.ItemIsDropEnabled
        return (
            qc.Qt.ItemFlag.ItemIsEnabled
            | qc.Qt.ItemFlag.ItemIsSelectable
            | qc.Qt.ItemFlag.ItemIsUserCheckable
            | qc.Qt.ItemFlag.ItemIsDragEnabled
            | qc.Qt.ItemFlag.ItemIsDropEnabled
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
