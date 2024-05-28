#!/usr/bin/env python


import PySide6.QtCore as qc

from query import Query


class QueryTableModel(qc.QAbstractTableModel):

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)
        self.query = query

        self.query.query_changed.connect(self.update)

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.query.get_data())

    def columnCount(self, parent):
        if parent.isValid():
            return 0
        if self.query.get_data():
            return len(self.query.get_data()[0])
        return 0

    def data(self, index, role):
        if role == qc.Qt.ItemDataRole.DisplayRole:
            if index.row() < 0 or index.row() >= len(self.query.get_data()):
                return None
            if index.column() < 0 or index.column() >= len(self.query.get_data()[0]):
                return None
            return self.query.get_data()[index.row()][index.column()]

    def headerData(self, section, orientation, role):
        if section >= len(self.query.get_header()):
            return None
        if role == qc.Qt.ItemDataRole.DisplayRole:
            if orientation == qc.Qt.Orientation.Horizontal:
                return self.query.get_header()[section]

    def update(self):
        self.beginResetModel()
        self.endResetModel()
