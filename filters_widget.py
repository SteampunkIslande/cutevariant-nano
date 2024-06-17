import PySide6.QtWidgets as qw

import filters_model as fltm
from query import Query


class FiltersWidget(qw.QWidget):
    def __init__(self, query: Query, parent=None):
        super().__init__(parent)

        self._layout = qw.QVBoxLayout()
        self.setLayout(self._layout)

        self.filters = qw.QTreeView(self)
        self.model = fltm.FiltersItemModel(query.root_filter, self)
        self.filters.setModel(self.model)

        self._layout.addWidget(self.filters)

        self._layout.addStretch()

        self.query = query

        self.query.query_changed.connect(self.update_model)

        self.show()

    def update_model(self):
        if self.query.root_filter is not self.model.root:
            del self.model
            self.model = fltm.FiltersItemModel(self.query.root_filter, self)
            self.filters.setModel(self.model)
