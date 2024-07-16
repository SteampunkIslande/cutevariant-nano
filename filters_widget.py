import PySide6.QtWidgets as qw

from query import Query


class FiltersWidget(qw.QWidget):
    def __init__(self, query: Query, parent=None):
        super().__init__(parent)

        self._layout = qw.QVBoxLayout()
        self.setLayout(self._layout)

        self.filters = qw.QTreeView(self)
        self.model = query.filter_model
        self.filters.setModel(self.model)

        self._layout.addWidget(self.filters)

        self._layout.addStretch()

        self.query = query

        self.show()
