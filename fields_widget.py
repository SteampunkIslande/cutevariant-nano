import PySide6.QtWidgets as qw

import query as q


class FieldsWidget(qw.QWidget):
    def __init__(self, query: "q.Query", parent=None):
        super().__init__(parent)
        self.query = query
        self.model = query.fields_model

        self.view = qw.QListView(self)
        self.view.setModel(self.model)
        self.view.setSelectionMode(qw.QAbstractItemView.SelectionMode.SingleSelection)

        layout = qw.QVBoxLayout(self)
        layout.addWidget(self.view)
        self.setLayout(layout)
