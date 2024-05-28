from typing import List

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw


class SearchableList(qw.QWidget):

    def __init__(self, items: List[str], filter_type="fixed_string", parent=None):
        super().__init__(parent)

        self.items = items
        self.model = qg.QStandardItemModel(len(items), 1)
        for i, item_text in enumerate(items):
            item = qg.QStandardItem(item_text)
            item.setCheckable(True)
            self.model.setItem(i, 0, item)

        self.proxy_model = qc.QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(qc.Qt.CaseSensitivity.CaseInsensitive)

        self.view = qw.QListView()
        self.view.setModel(self.proxy_model)

        self.view.setSelectionMode(qw.QAbstractItemView.SelectionMode.NoSelection)

        self.filter_le = qw.QLineEdit()
        self.filter_le.setPlaceholderText("Filter list...")

        layout = qw.QVBoxLayout()
        layout.addWidget(self.filter_le)
        layout.addWidget(self.view)

        self.setLayout(layout)

        self.filter_le_callbacks = {
            "fixed_string": self.proxy_model.setFilterFixedString,
            "regexp": self.proxy_model.setFilterRegularExpression,
        }
        self.selected_filter_callback = self.filter_le_callbacks[filter_type]

        self.filter_le.textChanged.connect(self.on_filter_changed)

    def get_selected(self) -> str:
        return [
            self.model.item(i, 0).text()
            for i in range(len(self.items))
            if self.model.item(i, 0).checkState() == qc.Qt.CheckState.Checked
        ]

    def set_filter_type(self, filter_type):
        if filter_type in self.filter_le_callbacks:
            self.selected_filter_callback = self.filter_le_callbacks[filter_type]

    def on_filter_changed(self):
        self.selected_filter_callback(self.filter_le.text())


if __name__ == "__main__":
    app = qw.QApplication([])
    widget = SearchableList(["one", "two", "three"])
    widget.show()
    app.exec()
