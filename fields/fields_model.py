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

    def supportedDropActions(self):
        """Return the drop actions supported by this model."""
        return qc.Qt.DropAction.MoveAction

    def mimeTypes(self):
        """Return the list of MIME types supported by this model."""
        return ["application/x-fields-model-item"]

    def mimeData(self, indexes):
        """Create MIME data for the given indexes."""
        if not indexes:
            return None

        mime_data = qc.QMimeData()

        # Get the rows being dragged
        rows = sorted(set(index.row() for index in indexes))

        # Create a simple string representation of the rows
        data = ",".join(str(row) for row in rows)
        mime_data.setData("application/x-fields-model-item", data.encode("utf-8"))

        return mime_data

    def canDropMimeData(self, data, action, row, column, parent):
        """Check if the drop is allowed."""
        if parent.isValid():
            return False

        if not data.hasFormat("application/x-fields-model-item"):
            return False

        if action != qc.Qt.DropAction.MoveAction:
            return False

        return True

    def dropMimeData(self, data, action, row, column, parent):
        """Handle the drop of MIME data."""
        if not self.canDropMimeData(data, action, row, column, parent):
            return False

        if action == qc.Qt.DropAction.IgnoreAction:
            return True

        # Get the source rows
        source_data = (
            data.data("application/x-fields-model-item").data().decode("utf-8")
        )
        source_rows = [int(r) for r in source_data.split(",")]

        # Determine the destination row
        if row == -1:
            # Dropped on an item, insert after it
            if parent.isValid():
                dest_row = parent.row() + 1
            else:
                dest_row = len(self.fields)
        else:
            dest_row = row

        # Sort source rows in descending order to avoid index shifting issues
        source_rows.sort(reverse=True)

        # Extract the items to move
        items_to_move = []
        for source_row in source_rows:
            if 0 <= source_row < len(self.fields):
                items_to_move.append(self.fields[source_row])

        # Remove items from source positions (in reverse order)
        for source_row in source_rows:
            if 0 <= source_row < len(self.fields):
                self.beginRemoveRows(qc.QModelIndex(), source_row, source_row)
                del self.fields[source_row]
                self.endRemoveRows()

                # Adjust destination row if necessary
                if source_row < dest_row:
                    dest_row -= 1

        # Insert items at the destination
        if dest_row > len(self.fields):
            dest_row = len(self.fields)

        items_to_move.reverse()  # Reverse to maintain original order
        for i, item in enumerate(items_to_move):
            insert_row = dest_row + i
            self.beginInsertRows(qc.QModelIndex(), insert_row, insert_row)
            self.fields.insert(insert_row, item)
            self.endInsertRows()

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
