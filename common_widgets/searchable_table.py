from typing import List

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw


class SearchableTable(qw.QWidget):

    def __init__(
        self, model: qc.QAbstractItemModel, filter_type="fixed_string", parent=None
    ):
        super().__init__(parent)
        self.model = model

        self.proxy_model = qc.QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(qc.Qt.CaseSensitivity.CaseInsensitive)

        self.view = qw.QTableView()
        self.view.setModel(self.proxy_model)
        self.view.setSelectionBehavior(
            qw.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.view.setSelectionMode(qw.QAbstractItemView.SelectionMode.SingleSelection)
        self.view.horizontalHeader().setStretchLastSection(True)

        self.filter_le = qw.QLineEdit()
        self.filter_le.setPlaceholderText("Search...")

        layout = qw.QVBoxLayout()
        layout.addWidget(self.filter_le)
        layout.addWidget(self.view)

        self.setLayout(layout)

        self.proxy_model.setFilterKeyColumn(-1)

        self.filter_le_callbacks = {
            "fixed_string": self.proxy_model.setFilterFixedString,
            "regexp": self.proxy_model.setFilterRegularExpression,
        }
        self.selected_filter_callback = self.filter_le_callbacks[filter_type]

        self.filter_le.textChanged.connect(self.on_filter_changed)

    def set_model(self, model):
        self.model = model
        self.proxy_model.setSourceModel(model)

    def get_selected(self) -> List[qc.QModelIndex]:
        return self.view.selectedIndexes()

    def set_filter_type(self, filter_type):
        if filter_type in self.filter_le_callbacks:
            self.selected_filter_callback = self.filter_le_callbacks[filter_type]

    def on_filter_changed(self):
        self.selected_filter_callback(self.filter_le.text())
