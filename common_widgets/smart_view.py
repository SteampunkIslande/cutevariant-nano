from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *


class ColumnSelectionProxy(QSortFilterProxyModel):

    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self.column = -1
        self.hidden_rows = []

    def set_column(self, column: int):
        self.column = column
        self.invalidateColumnsFilter()

    def hide_row_indexes(self, row_indexes: list[int]):
        self.hidden_rows = row_indexes
        self.invalidateRowsFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        return source_row not in self.hidden_rows

    def filterAcceptsColumn(self, source_column, source_parent):
        if source_parent.isValid():
            return False
        return self.column == source_column


class SmartView(QWidget):

    def __init__(self, model: QAbstractItemModel = None, parent: QWidget = None):
        super().__init__(parent)

        self._layout = QVBoxLayout()

        self.filter_le = QLineEdit()
        self.list_view = QListView()
        self.table_view = QTableView()

        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().hide()

        self.model: QAbstractItemModel = None

        self.list_filter_model = QSortFilterProxyModel()
        self.transposition_model: QTransposeProxyModel = QTransposeProxyModel()
        self.column_selection_model: ColumnSelectionProxy = ColumnSelectionProxy()

        self.set_model(model)

        self._layout.addWidget(self.filter_le)
        self._layout.addWidget(self.list_view)
        self._layout.addWidget(self.table_view)

        self.list_view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.list_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.list_view_col = 0

        self.setLayout(self._layout)

    def set_list_view_column(self, col: int):
        self.list_view.setModelColumn(col)
        self.list_view_col = self.list_view.modelColumn()
        self.list_filter_model.setFilterKeyColumn(self.list_view.modelColumn())

    def set_model(self, model: QAbstractItemModel):
        if model is None:
            return
        if self.model:
            self.list_view.selectionModel().currentRowChanged.disconnect(
                self.update_selected_col
            )
            self.filter_le.textChanged.disconnect(self.update_list_filter)

        self.model = model
        self.list_filter_model.setSourceModel(self.model)
        self.transposition_model.setSourceModel(self.model)

        self.column_selection_model.setSourceModel(self.transposition_model)

        self.list_view.setModel(self.list_filter_model)
        self.list_view.selectionModel().currentRowChanged.connect(
            self.update_selected_col
        )

        self.filter_le.textChanged.connect(self.update_list_filter)

        self.table_view.setModel(self.column_selection_model)

    def update_list_filter(self, text: str):
        self.list_filter_model.setFilterFixedString(text)

    def update_selected_col(self, cur: QModelIndex, prev: QModelIndex):
        self.column_selection_model.set_column(cur.row())


if __name__ == "__main__":

    app = QApplication()

    model = QStandardItemModel()

    view = SmartView(model)

    data = [
        {
            "chromosome": "chr7",
            "position": 42,
            "gnomad_AF": 0.1,
            "sample_name": "sacha",
            "variant": "variant A",
        },
        {
            "chromosome": "chr12",
            "position": 105,
            "gnomad_AF": 0.05,
            "sample_name": "alex",
            "variant": "variant B",
        },
        {
            "chromosome": "chr3",
            "position": 78,
            "gnomad_AF": 0.2,
            "sample_name": "morgan",
            "variant": "variant C",
        },
        {
            "chromosome": "chr19",
            "position": 150,
            "gnomad_AF": 0.15,
            "sample_name": "jordan",
            "variant": "variant D",
        },
        {
            "chromosome": "chr5",
            "position": 200,
            "gnomad_AF": 0.08,
            "sample_name": "taylor",
            "variant": "variant E",
        },
    ]
    col_names = list(data[0].keys())

    for row in data:
        model_row = []
        for colname in col_names:
            item = QStandardItem()
            item.setData(row[colname], Qt.ItemDataRole.DisplayRole)
            item.setData(row[colname], Qt.ItemDataRole.UserRole)
            model_row.append(item)
        model.appendRow(model_row)

    for i, col_name in enumerate(col_names):
        model.setHeaderData(
            i, Qt.Orientation.Horizontal, col_name, Qt.ItemDataRole.DisplayRole
        )
    view.set_list_view_column(4)

    view.show()
    exit(app.exec())
