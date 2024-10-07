#!/usr/bin/env python


import json

import PySide6.QtCore as qc
import PySide6.QtGui as qg

from commons import get_config_folder, load_user_prefs
from query import Query


def load_style():
    prefs = load_user_prefs()
    style: str = prefs.get("column_styles", "style42.json")
    style_file_path = (get_config_folder() / "styles" / style).resolve()
    if style_file_path.is_file():
        with open(style_file_path, "r", encoding="utf-8") as f:
            return json.load(f)


def style_from_index(style: dict, index: qc.QModelIndex):
    # Read from config file
    colname = index.model().headerData(index.column(), qc.Qt.Orientation.Horizontal)
    row_data = index.data(qc.Qt.ItemDataRole.UserRole)

    base_style = {}
    base_style_def = style.get("*", {})
    for style_key in base_style_def:
        style_origin = list(base_style_def[style_key].keys())[0]
        if style_origin == "from_column":
            base_style[style_key] = row_data.get(
                base_style_def[style_key]["from_column"], ""
            )
        elif style_origin == "constant":
            base_style[style_key] = base_style_def[style_key]["constant"]

    style_def = style.get(colname, {})
    if not style_def:
        return base_style
    for style_key in style_def:
        style_origin = list(style_def[style_key].keys())[0]
        if style_origin == "from_column":
            base_style[style_key] = row_data.get(
                style_def[style_key]["from_column"], ""
            )
        elif style_origin == "constant":
            base_style[style_key] = style_def[style_key]["constant"]

    return base_style


class QueryTableModel(qc.QAbstractTableModel):

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)
        self.query = query

        self.header = self.query.get_header()
        self._data = self.query.get_data()

        self.query.query_changed.connect(self.update)

        self.style = load_style()

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

        if role == qc.Qt.ItemDataRole.UserRole:
            return {
                str(colname): str(val)
                for colname, val in zip(self.header, self._data[index.row()])
            }
        draw_options = style_from_index(self.style, index)

        if role == qc.Qt.ItemDataRole.ForegroundRole:
            background_color = self.data(index, qc.Qt.ItemDataRole.BackgroundRole)
            if background_color is not None:
                if isinstance(background_color, qg.QColor):
                    return qg.QColor.fromRgb(
                        255 - background_color.red(),
                        255 - background_color.green(),
                        255 - background_color.blue(),
                    )
            if (
                "color" in draw_options
                and draw_options["color"]
                and draw_options["color"] != "None"
            ):
                return qg.QColor(draw_options["color"])
            else:
                return
        if role == qc.Qt.ItemDataRole.BackgroundRole:
            if "background" in draw_options and draw_options["background"]:
                if draw_options["background"].startswith("#"):
                    if draw_options["background"] == "#FF000000":
                        return
                    if len(draw_options["background"]) == 7:
                        return qg.QColor.fromRgb(
                            int(draw_options["background"][1:], 16)
                        )
                    else:
                        return qg.QColor.fromRgba(
                            int(draw_options["background"][1:], 16)
                        )
                return qg.QColor(draw_options["background"])
        if role == qc.Qt.ItemDataRole.FontRole:
            if "bold" in draw_options:
                font = qg.QFont()
                font.setBold(True)
                return font

        return

    def headerData(self, section, orientation, role=qc.Qt.ItemDataRole.DisplayRole):
        if section >= len(self.header):
            return None
        if role == qc.Qt.ItemDataRole.DisplayRole:
            if orientation == qc.Qt.Orientation.Horizontal:
                return str(self.header[section])

    def update(self):
        self.beginResetModel()
        self.header = self.query.get_header()
        self._data = self.query.get_data()
        self.endResetModel()
