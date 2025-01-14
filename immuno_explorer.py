import PySide6.QtWidgets as qw

import query as q
from query_table_widget import QueryTableWidget
from validation_widget import ValidationWidget


class ImmunoExplorer(qw.QWidget):

    def __init__(
        self,
        query: "q.Query",
        query_table_widget: QueryTableWidget,
        validation_widget: ValidationWidget,
        parent=None,
    ):
        super().__init__(parent)

        self._layout = qw.QVBoxLayout()

        self.query = query

        self.setLayout(self._layout)
