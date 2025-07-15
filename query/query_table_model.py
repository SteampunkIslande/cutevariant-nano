#!/usr/bin/env python

import PySide6.QtCore as qc

import query.query_component as q_cmp


class QueryTableModel(qc.QAbstractTableModel):

    def __init__(self, query: "q_cmp.QueryComponent", parent=None):
        super().__init__(parent)
        self.query = query

        self.header = self.query.get_header()
        self._data = self.query.get_data()

        self.query.query_changed.connect(self.update)

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self._data)

    def columnCount(self, parent):
        if parent.isValid():
            return 0
        if self._data:
            return len(self._data[0])
        return 0

    def data(self, index: qc.QModelIndex, role=qc.Qt.ItemDataRole.DisplayRole):
        if role in (qc.Qt.ItemDataRole.DisplayRole, qc.Qt.ItemDataRole.ToolTipRole):
            if index.row() < 0 or index.row() >= len(self._data):
                return None
            if index.column() < 0 or index.column() >= len(self._data[0]):
                return None

            res = self._data[index.row()][index.column()]

            if res is None:
                res = "NULL"
            return str(res)

        if role == qc.Qt.ItemDataRole.UserRole:
            return {
                str(colname): str(val)
                for colname, val in zip(self.header, self._data[index.row()])
            }
        return None

    def headerData(self, section, orientation, role=qc.Qt.ItemDataRole.DisplayRole):
        if section >= len(self.header):
            return None
        if orientation == qc.Qt.Orientation.Horizontal:
            if role == qc.Qt.ItemDataRole.DisplayRole:
                return str(self.header[section])
            if role == qc.Qt.ItemDataRole.InitialSortOrderRole:
                colname = self.header[section]
                if self.query.order_by is not None and colname in self.query.order_by:
                    if self.query.order_by[colname] == "ASC":
                        return qc.Qt.SortOrder.AscendingOrder
                    else:
                        return qc.Qt.SortOrder.DescendingOrder

    def update(self):
        self.beginResetModel()
        self.header = self.query.get_header()
        self._data = self.query.get_data()
        self.endResetModel()
