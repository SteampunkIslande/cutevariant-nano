#!/usr/bin/env python


from functools import partial

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

from common_widgets.page_selector import PageSelector
from filters import FilterType
from query import Query
from query_table_model import QueryTableModel


class QueryTableProxyModel(qc.QSortFilterProxyModel):
    # Automatically hides columns which names start with a dot
    def filterAcceptsColumn(self, source_column: int, source_parent: qc.QModelIndex):
        source_model = self.sourceModel()
        header: str = source_model.headerData(
            source_column, qc.Qt.Orientation.Horizontal
        )
        return not header.startswith(".")

    # Rename columns by splitting on every colon
    def headerData(self, section: int, orientation: qc.Qt.Orientation, role: int):
        source_model = self.sourceModel()
        actual_section = self.mapToSource(self.index(0, section)).column()
        header: str = source_model.headerData(actual_section, orientation, role)
        if role == qc.Qt.ItemDataRole.DisplayRole:
            return header.split(":")[0] if header else header
        return header


class QueryTableWidget(qw.QWidget):

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)

        self.query = query
        self.model = QueryTableModel(query)
        self.proxy_model = QueryTableProxyModel()
        self.proxy_model.setSourceModel(self.model)

        self.table_view = qw.QTableView()
        self.table_view.setSelectionBehavior(
            qw.QAbstractItemView.SelectionBehavior.SelectRows
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
        self.table_view.setModel(self.proxy_model)

        self.page_selector = PageSelector(query)

        layout = qw.QVBoxLayout()
        layout.addWidget(self.table_view)
        layout.addWidget(self.page_selector)

        self.setLayout(layout)

    def show_header_context_menu(self, pos):
        menu = qw.QMenu()

        index = self.table_view.indexAt(pos)

        filter_action = menu.addAction(
            qc.QCoreApplication.tr("Filtrer cette colonne (simple expression)")
        )
        filter_action.triggered.connect(partial(self.filter_column, index))
        menu.exec_(self.table_view.mapToGlobal(pos))

    def filter_column(self, index: qc.QModelIndex):

        col_name = index.model().headerData(
            index.column(), qc.Qt.Orientation.Horizontal
        )
        dialog = qw.QInputDialog(self)
        dialog.setInputMode(qw.QInputDialog.InputMode.TextInput)
        dialog.setLabelText(qc.QCoreApplication.tr(f"Filter {col_name}"))
        dialog.setWindowTitle(qc.QCoreApplication.tr("Filtrer une colonne"))
        dialog.setOkButtonText(qc.QCoreApplication.tr("Filtrer"))

        if dialog.exec_() == qw.QDialog.DialogCode.Accepted:
            filter_text = dialog.textValue()
            self.query.filter_model.add_filter(
                self.query.filter_model.index(0, 0),
                FilterType.LEAF,
                f"{col_name} {filter_text}",
            )
