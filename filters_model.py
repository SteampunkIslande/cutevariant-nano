import sys
from typing import Any

from PySide6.QtCore import QAbstractItemModel, QModelIndex, QObject, QPoint, Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication,
    QHeaderView,
    QMenu,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from filters import FilterItem, FilterType

# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause


class FilterModel(QAbstractItemModel):
    """An editable model of tree data"""

    model_changed = Signal()

    def __init__(self, parent: QObject = None):
        super().__init__(parent)

        self._rootItem = FilterItem(FilterType.ROOT)

    def clear(self):
        """Clear data from the model"""
        # Set the model to its minimal state
        self.load(
            {
                "filter_type": "ROOT",
                "children": [{"filter_type": "AND", "children": []}],
            }
        )
        self.model_changed.emit()

    def add_child(self, parent: QModelIndex, item: FilterItem):
        """Add a child to the parent index"""
        if not parent.isValid():
            parentItem: FilterItem = self._rootItem
            print("Cannot add to root")
            # Cannot add anything to the root item other than the default AND or OR actual root
            return False
        else:
            parentItem: FilterItem = parent.internalPointer()

        self.beginInsertRows(parent, parentItem.child_count(), parentItem.child_count())
        parentItem.add_child(item)
        self.endInsertRows()

        self.model_changed.emit()
        return True

    def add_filter(self, expression: str):
        """Add a filter to the root element of the model"""
        index = self.index(0, 0, self.index(0, 0, self.index(0, 0)))
        self.add_child(index, FilterItem(FilterType.LEAF, expression=expression))

    def remove_child(self, index: QModelIndex):
        """Remove a child from the parent index"""
        if not index.isValid():
            print("Invalid index")
            return False

        item: FilterItem = index.internalPointer()
        parent: FilterItem = index.parent().internalPointer()

        if not item.can_remove_child():
            print("Cannot remove child")
            return False

        row = item.row()

        self.beginRemoveRows(index.parent(), row, row)
        parent.remove_child(row)
        self.endRemoveRows()

        self.model_changed.emit()

        return True

    def load(self, document: dict):
        """Load model from a nested dictionary returned by json.loads()

        Arguments:
            document (dict): JSON-compatible dictionary
        """

        self.beginResetModel()

        self._rootItem = FilterItem.from_json(document)
        self.endResetModel()

        self.model_changed.emit()
        return True

    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> Any:
        """Override from QAbstractItemModel

        Return data from a json item according index and role

        """
        if not index.isValid():
            return None

        item: FilterItem = index.internalPointer()

        if role == Qt.ItemDataRole.DisplayRole:
            return item.display()

    def setData(self, index: QModelIndex, value: dict, role: Qt.ItemDataRole):
        """Override from QAbstractItemModel

        Set json item according index and role

        Args:
            index (QModelIndex)
            value (Any)
            role (Qt.ItemDataRole)

        """
        if role == Qt.ItemDataRole.EditRole:

            item: FilterItem = index.internalPointer()
            if item.update_single(value):
                self.dataChanged.emit(index, index, [Qt.ItemDataRole.EditRole])
                self.model_changed.emit()
                return True

        return False

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole
    ):
        """Override from QAbstractItemModel

        For the JsonModel, it returns only data for columns (orientation = Horizontal)

        """
        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == Qt.Orientation.Horizontal:
            return "Filter"

    def index(self, row: int, column: int, parent=QModelIndex()) -> QModelIndex:
        """Override from QAbstractItemModel

        Return index according row, column and parent

        """
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self._rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        """Override from QAbstractItemModel

        Return parent index of index

        """

        if not index.isValid():
            return QModelIndex()

        childItem: FilterItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self._rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent=QModelIndex()):
        """Override from QAbstractItemModel

        Return row count from parent index
        """
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parentItem = self._rootItem
        else:
            parentItem: FilterItem = parent.internalPointer()

        return parentItem.child_count()

    def columnCount(self, parent=QModelIndex()):
        """Override from QAbstractItemModel

        Return column number. For the model, it always return 1 columns
        """
        return 1

    def to_dict(self):
        return self._rootItem.to_json()

    def __str__(self) -> str:
        return str(self._rootItem)

    def is_empty(self):
        return (
            self._rootItem.child_count() == 0
            or self._rootItem.child(0).child_count() == 0
        )


class TestWidget(QWidget):

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.view = QTreeView()
        self.model = FilterModel()

        self.view.setModel(self.model)

        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.model.load(
            {
                "filter_type": "ROOT",
                "children": [
                    {
                        "filter_type": "AND",
                        "children": [
                            {
                                "filter_type": "LEAF",
                                "expression": "a = 5",
                                "alias": None,
                            },
                            {
                                "filter_type": "LEAF",
                                "expression": "b = 6",
                                "alias": None,
                            },
                            {
                                "filter_type": "OR",
                                "children": [
                                    {
                                        "filter_type": "LEAF",
                                        "expression": "c = 7",
                                        "alias": None,
                                    }
                                ],
                                "alias": None,
                            },
                        ],
                        "alias": None,
                    }
                ],
            }
        )

        self._layout = QVBoxLayout(self)
        self._layout.addWidget(self.view)
        self.setLayout(self._layout)

        self.view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.view.setAlternatingRowColors(True)
        self.view.resize(500, 300)

        self.view.customContextMenuRequested.connect(self.context_menu_requested)

    def add_child(self):
        index = self.view.currentIndex()
        if not index.isValid():
            return
        print("Before", self.model.to_dict())
        self.model.add_child(index, FilterItem(FilterType.LEAF, "a=3"))
        print("After", self.model.to_dict())

    def remove_child(self):
        print("Before")
        print(self.model.to_dict())
        index = self.view.currentIndex()
        if not index.isValid():
            return

        self.model.remove_child(index)

        print("After")
        print(self.model.to_dict())

    def context_menu_requested(self, p: QPoint):
        menu = QMenu()
        add_child_action = menu.addAction("Add Child")
        delete_item_action = menu.addAction("Delete")

        add_child_action.triggered.connect(self.add_child)
        delete_item_action.triggered.connect(self.remove_child)
        menu.exec(QCursor.pos())


if __name__ == "__main__":

    app = QApplication(sys.argv)

    w = TestWidget()
    w.show()

    app.exec()
