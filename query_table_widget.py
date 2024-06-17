#!/usr/bin/env python


from functools import partial

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

from common_widgets.page_selector import PageSelector
from filters import FilterItem, FilterType
from query import Query
from query_table_model import QueryTableModel


class QueryTableWidget(qw.QWidget):

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)

        self.query = query
        self.model = QueryTableModel(query)

        self.table_view = qw.QTableView()
        self.table_view.setSelectionBehavior(
            qw.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table_view.setSelectionMode(
            qw.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table_view.horizontalHeader().setStretchLastSection(
            True
        )  # Set last column to expand
        self.table_view.horizontalHeader().setContextMenuPolicy(
            qg.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.table_view.horizontalHeader().customContextMenuRequested.connect(
            self.show_header_context_menu
        )
        self.table_view.setModel(self.model)

        self.page_selector = PageSelector(query)

        layout = qw.QVBoxLayout()
        layout.addWidget(self.table_view)
        layout.addWidget(self.page_selector)

        self.setLayout(layout)

    def show_header_context_menu(self, pos):
        menu = qw.QMenu()

        index = self.table_view.indexAt(pos)
        print(index.model().headerData(index.column(), qc.Qt.Orientation.Horizontal))

        filter_action = menu.addAction("Filtrer cette colonne (simple expression)")
        filter_action.triggered.connect(partial(self.filter_column, index))
        menu.exec_(self.table_view.mapToGlobal(pos))

    def filter_column(self, index: qc.QModelIndex):

        col_name = index.model().headerData(
            index.column(), qc.Qt.Orientation.Horizontal
        )
        dialog = qw.QInputDialog(self)
        dialog.setInputMode(qw.QInputDialog.InputMode.TextInput)
        dialog.setLabelText(f"Filter {col_name}")
        dialog.setWindowTitle("Filter column")
        dialog.setOkButtonText("Filter")
        dialog.setCancelButtonText("Cancel")

        if dialog.exec_() == qw.QDialog.DialogCode.Accepted:
            filter_text = dialog.textValue()
            self.model.query.add_filter(
                FilterItem(FilterType.LEAF, f"{col_name} {filter_text}")
            )
