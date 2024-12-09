# A model to selected fields using checkboxes


import PySide6.QtCore as qc

import query as q


class FieldsModel(qc.QAbstractListModel):

    def __init__(self, query: "q.Query", parent=None):
        super().__init__(parent)
        self.fields = []
        self.query = query

        self.query.query_changed.connect(self.load)

    def load(self):
        self.beginResetModel()
        fields = self.query.list_exposed_fields()
        print(fields)
        previous_selected_fields = self.checked_fields()
        if len(previous_selected_fields) == 0:
            self.fields = [[field, True] for field in fields]
        else:
            self.fields = [
                [field, field in previous_selected_fields] for field in fields
            ]
        self.endResetModel()

    def rowCount(self, parent=qc.QModelIndex()):
        return len(self.fields)

    def data(self, index, role=qc.Qt.ItemDataRole.DisplayRole):
        if role == qc.Qt.ItemDataRole.DisplayRole:
            return self.fields[index.row()]
        return None

    def flags(self, index):
        return qc.Qt.ItemFlag.ItemIsUserCheckable | qc.Qt.ItemFlag.ItemIsEnabled

    def setData(self, index, value, role=qc.Qt.ItemDataRole.CheckStateRole):
        if role == qc.Qt.ItemDataRole.CheckStateRole:
            self.fields[index.row()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def checked_fields(self):
        return [field_name for field_name, checked in self.fields if checked]

    def unchecked_fields(self):
        return [field_name for field_name, checked in self.fields if not checked]

    def check_all(self):
        for i, field in enumerate(self.fields):
            field[1] = True
            self.dataChanged.emit(self.index(i), self.index(i))

    def uncheck_all(self):
        for i, field in enumerate(self.fields):
            field[1] = False
            self.dataChanged.emit(self.index(i), self.index(i))

    def invert_check(self):
        for i, field in enumerate(self.fields):
            field[1] = not field[1]
            self.dataChanged.emit(self.index(i), self.index(i))

    # def supportedDropActions(self):
    #     return qc.Qt.DropAction.MoveAction

    # def flags(self, index):
    #     default_flags = super().flags(index)
    #     return (
    #         default_flags
    #         | qc.Qt.ItemFlag.ItemIsDragEnabled
    #         | qc.Qt.ItemFlag.ItemIsDropEnabled
    #     )

    # def mimeTypes(self):
    #     return []

    # def mimeData(self, indexes):
    #     mime_data = qc.QMimeData()

    #     for index in indexes:
    #         if index.isValid():
    #             text = self.data(index, qc.Qt.ItemDataRole.DisplayRole)
    #             mime_data.setText(text)
    #     return mime_data

    # def dropMimeData(self, data, action, row, column, parent):
    #     if action == qc.Qt.DropAction.IgnoreAction:
    #         return True
    #     if not data.hasText():
    #         return False
    #     if row == -1:
    #         row = parent.row()
    #     self.insertRows(row, 1, qc.QModelIndex())
    #     self.fields[row] = [data.text(), True]
    #     return True

    # def removeRows(self, row, count, parent=qc.QModelIndex()):
    #     self.beginRemoveRows(parent, row, row + count - 1)
    #     del self.fields[row : row + count]
    #     self.endRemoveRows()
    #     return True
