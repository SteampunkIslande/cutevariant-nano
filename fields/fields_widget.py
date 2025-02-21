import PySide6.QtWidgets as qw

import query.query as q
from common_widgets.searchable_list import SearchableList


class FieldsWidget(qw.QWidget):
    def __init__(self, query: "q.Query", parent=None):
        super().__init__(parent)
        self.query = query
        self.model = query.fields_model

        self.searchable_list = SearchableList(self.model)
        self.searchable_list.view.setDragDropMode(
            qw.QAbstractItemView.DragDropMode.InternalMove
        )

        layout = qw.QVBoxLayout(self)
        layout.addWidget(self.searchable_list)
        self.setLayout(layout)
