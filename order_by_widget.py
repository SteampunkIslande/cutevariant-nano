import PySide6.QtWidgets as qw

from order_by_model import OrderByModel
from query import Query


class OrderByWidget(qw.QWidget):
    def __init__(self, query: Query, parent=None):
        super().__init__(parent)

        self.query = query

        self._layout = qw.QVBoxLayout()
        self.setLayout(self._layout)

        self.setup_model_view()

        self._layout.addStretch()

        self.show()

    def on_model_changed(self):
        self.query.order_by = self.order_by_model.get_data()

    def setup_model_view(self):
        self.order_by_view = qw.QTableView(self)
        self.order_by_model = OrderByModel(self)
        self.order_by_view.setModel(self.order_by_model)

        self.order_by_model.dataChanged.connect(self.on_model_changed)

        self.order_by_view.horizontalHeader().setSectionResizeMode(
            qw.QHeaderView.ResizeMode.ResizeToContents
        )
        self.order_by_view.horizontalHeader().setSectionResizeMode(
            0, qw.QHeaderView.ResizeMode.Stretch
        )
        self.order_by_view.horizontalHeader().setSectionResizeMode(
            1, qw.QHeaderView.ResizeMode.Stretch
        )

        self.order_by_view.setDragDropMode(
            qw.QAbstractItemView.DragDropMode.InternalMove
        )

        self._layout.addWidget(self.order_by_view)
