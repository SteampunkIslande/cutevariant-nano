# A model to selected fields using checkboxes


import PySide6.QtCore as qc
import PySide6.QtGui as qg

import query.query as q

# class FieldsModel(qc.QAbstractListModel):

#     model_changed = qc.Signal()

#     def __init__(self, query: "q.Query", parent=None):
#         super().__init__(parent)
#         self.fields = []
#         self.query = query

#         self.query.query_setup_changed.connect(self.load)

#     def load(self):
#         self.beginResetModel()
#         fields = self.query.list_exposed_fields()
#         self.fields = [[field, True] for field in fields]
#         self.endResetModel()

#     def rowCount(self, parent=qc.QModelIndex()):
#         return len(self.fields)

#     def data(self, index, role=qc.Qt.ItemDataRole.DisplayRole):
#         if role == qc.Qt.ItemDataRole.DisplayRole:
#             return self.fields[index.row()][0]
#         if role == qc.Qt.ItemDataRole.CheckStateRole:
#             return (
#                 qc.Qt.CheckState.Checked
#                 if self.fields[index.row()][1]
#                 else qc.Qt.CheckState.Unchecked
#             )
#         return None

#     def setData(self, index, value, role):
#         if role == qc.Qt.ItemDataRole.CheckStateRole:
#             self.fields[index.row()][1] = (
#                 True if value == qc.Qt.CheckState.Checked else False
#             )
#             self.dataChanged.emit(index, index)
#             self.model_changed.emit()
#             return True
#         return False

#     def checked_fields(self):
#         return [field_name for field_name, checked in self.fields if checked]

#     def unchecked_fields(self):
#         return [field_name for field_name, checked in self.fields if not checked]

#     def check_all(self):
#         for i, field in enumerate(self.fields):
#             field[1] = True
#             self.dataChanged.emit(self.index(i), self.index(i))
#         self.model_changed.emit()

#     def uncheck_all(self):
#         for i, field in enumerate(self.fields):
#             field[1] = False
#             self.dataChanged.emit(self.index(i), self.index(i))
#         self.model_changed.emit()

#     def invert_check(self):
#         for i, field in enumerate(self.fields):
#             field[1] = not field[1]
#             self.dataChanged.emit(self.index(i), self.index(i))
#         self.model_changed.emit()

#     def supportedDropActions(self):
#         return qc.Qt.DropAction.MoveAction

#     def flags(self, index):
#         default_flags = super().flags(index)
#         return (
#             default_flags
#             | qc.Qt.ItemFlag.ItemIsDragEnabled
#             | qc.Qt.ItemFlag.ItemIsDropEnabled
#         )

#     def mimeTypes(self):
#         return ["text/plain"]

#     def mimeData(self, indexes):
#         mime_data = qc.QMimeData()
#         if len(indexes) != 1:
#             return mime_data

#         index = indexes[0]
#         if index.isValid():
#             text = f"{index.row()}\t{self.data(index, qc.Qt.ItemDataRole.DisplayRole)}"
#             mime_data.setText(text)
#         return mime_data

#     def moveRow(self, sourceParent, sourceRow, destinationParent, destinationChild):
#         if sourceParent != destinationParent:
#             return False
#         if sourceRow == destinationChild:
#             return False
#         self.beginMoveRows(
#             sourceParent, sourceRow, sourceRow + 1, destinationParent, destinationChild
#         )
#         self.fields.insert(destinationChild, self.fields.pop(sourceRow))
#         self.endMoveRows()
#         self.model_changed.emit()

#     def canDropMimeData(self, data, action, row, column, parent):
#         if parent.isValid():
#             return False
#         if action == qc.Qt.DropAction.MoveAction:
#             if data.hasText():
#                 return True
#         return False

#     def dropMimeData(self, data, action, row, column, parent):
#         if action == qc.Qt.DropAction.IgnoreAction:
#             return True
#         if not data.hasText():
#             return False
#         if row == -1:
#             row = 0
#         source_row, text = data.text().split("\t")
#         source_row = int(source_row)
#         self.moveRow(qc.QModelIndex(), source_row, qc.QModelIndex(), row)
#         return True

#     def removeRows(self, row, count, parent=qc.QModelIndex()):
#         self.beginRemoveRows(parent, row, row + count - 1)
#         del self.fields[row : row + count]
#         self.endRemoveRows()
#         return True


class FieldsModel(qg.QStandardItemModel):

    model_changed = qc.Signal()

    def __init__(self, query: "q.Query", parent=None):
        super().__init__(parent)
        self.query = query

        self.query.query_setup_changed.connect(self.load)

        self.rowsMoved.connect(lambda _: self.model_changed.emit)
        self.rowsRemoved.connect(lambda _: self.model_changed.emit)

    def load(self):
        self.clear()
        self.fields = self.query.list_exposed_fields()
        for i, field in enumerate(self.fields):
            item = qg.QStandardItem(field)
            item.setData(i, qc.Qt.ItemDataRole.UserRole)
            item.setDragEnabled(True)
            item.setCheckable(True)
            item.setCheckState(qc.Qt.CheckState.Checked)
            self.appendRow(item)

    def checked_fields(self):
        return [
            self.item(i).text()
            for i in range(self.rowCount())
            if self.item(i).checkState() == qc.Qt.CheckState.Checked
        ]
