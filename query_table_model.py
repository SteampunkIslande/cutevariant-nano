#!/usr/bin/env python


import PySide6.QtCore as qc
import PySide6.QtGui as qg

from query import Query


def style_from_colname(colname: str):
    _, *options = colname.split(":")
    if not options:
        return {}
    return dict([opt.split("=") for opt in options])


class QueryTableModel(qc.QAbstractTableModel):

    def __init__(self, query: Query, parent=None):
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
        if role == qc.Qt.ItemDataRole.DisplayRole:
            if index.row() < 0 or index.row() >= len(self._data):
                return None
            if index.column() < 0 or index.column() >= len(self._data[0]):
                return None

            return str(self._data[index.row()][index.column()])

    def headerData(self, section, orientation, role=qc.Qt.ItemDataRole.DisplayRole):
        if section >= len(self.header):
            return None
        if role == qc.Qt.ItemDataRole.DisplayRole:
            if orientation == qc.Qt.Orientation.Horizontal:
                return str(self.header[section])

        draw_options = style_from_colname(self.header[section])

        if role == qc.Qt.ItemDataRole.ForegroundRole:
            if "color" in draw_options:
                return qg.QColor(draw_options["color"])
        if role == qc.Qt.ItemDataRole.BackgroundRole:
            if "background" in draw_options:
                return qg.QColor(draw_options["background"])
        if role == qc.Qt.ItemDataRole.FontRole:
            if "bold" in draw_options:
                font = qg.QFont()
                font.setBold(True)
                return font

    def update(self):
        self.beginResetModel()
        self.header = self.query.get_header()
        self._data = self.query.get_data()
        self.endResetModel()
