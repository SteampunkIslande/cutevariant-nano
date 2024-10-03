import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

from filters import FilterItem, FilterType
from query import Query


class FiltersWidget(qw.QWidget):
    def __init__(self, query: Query, parent=None):
        super().__init__(parent)

        self._layout = qw.QVBoxLayout()
        self.setLayout(self._layout)

        self.filters_view = qw.QTreeView(self)
        # Add context menu with actions to add, remove, and move filters
        self.filters_view.setContextMenuPolicy(
            qc.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.filters_view.customContextMenuRequested.connect(
            self.context_menu_requested
        )
        self.model = query.filter_model
        self.filters_view.setModel(self.model)

        self._layout.addWidget(self.filters_view)

        self._layout.addStretch()

        self.query = query

        self.show()

    def add_filter_leaf(self):
        index = self.filters_view.currentIndex()
        if not index.isValid():
            return
        expression = qw.QInputDialog.getText(self, "Expression", "Enter expression")
        item = FilterItem(FilterType.LEAF, expression, None)
        self.model.add_child(index, item)

    def remove_filter(self):
        index = self.filters_view.currentIndex()
        if not index.isValid():
            return
        self.model.remove_child(index)

    def context_menu_requested(self, pos):
        menu = qw.QMenu(self)

        add_filter_action = menu.addAction("Add filter")
        add_filter_action.triggered.connect(self.add_filter_leaf)

        remove_filter_action = menu.addAction("Remove filter")
        remove_filter_action.triggered.connect(self.remove_filter)

        menu.exec_(self.filters_view.viewport().mapToGlobal(pos))
