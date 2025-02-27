import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

import common_widgets.searchable_list as s_list


class FormModelView(qw.QWidget):

    def __init__(self, model: qc.QAbstractItemModel, parent: qw.QWidget = None):
        super().__init__()
        self._layout = qw.QVBoxLayout()
        self.form_layout = qw.QFormLayout()

        self.model = model
        self.list_view = s_list.SearchableList(self.model, parent=self)

        self.list_view.view.selectionModel().currentRowChanged.connect(
            self.update_form_layout
        )
        self._layout.addWidget(self.list_view)
        self._layout.addLayout(self.form_layout)

        self.widgets = {}
        self.current_row = 0

        self.model_column = 0

        self.setLayout(self._layout)

        self.update_form_layout()

    def set_model_column(self, column: int):
        self.model_column = column
        self.list_view.set_model_column(column)

    def update_form_layout(self):

        self.current_row = self.list_view.view.currentIndex().row()
        self.list_view.set_model_column(self.model_column)

        if self.form_layout.count() != self.model.columnCount():
            self.build_form_layout()

        if self.current_row > self.model.rowCount() or self.current_row < 0:
            return

        for colid in range(self.model.columnCount()):
            colname = self.model.headerData(colid, qc.Qt.Orientation.Horizontal)

            # Important part
            self.widgets[colname].setText(
                self.model.index(self.current_row, colid).data(
                    qc.Qt.ItemDataRole.DisplayRole
                )
            )
            self.widgets[colname].setToolTip(
                self.model.index(self.current_row, colid).data(
                    qc.Qt.ItemDataRole.DisplayRole
                )
            )

    def build_form_layout(self):
        while self.form_layout.count():
            self.form_layout.removeRow(0)

        for colid in range(self.model.columnCount()):
            colname = self.model.headerData(colid, qc.Qt.Orientation.Horizontal)
            label = qw.QLabel("")
            label.setWordWrap(True)
            self.widgets[colname] = label  # Important part
            self.form_layout.addRow(colname, self.widgets[colname])
