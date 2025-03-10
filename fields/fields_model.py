# A model to selected fields using checkboxes


import PySide6.QtCore as qc
import PySide6.QtGui as qg

import query.query_component as q


class FieldsModel(qg.QStandardItemModel):

    model_changed = qc.Signal()

    def __init__(self, query: "q.QueryComponent", parent=None):
        super().__init__(parent)
        self.query = query

        self.query.query_setup_changed.connect(self.load)

        self.rowsMoved.connect(lambda _: self.model_changed.emit)
        self.rowsRemoved.connect(lambda _: self.model_changed.emit)

    def load(self):
        self.clear()
        self.fields = self.query.list_exposed_fields()
        for i, field in enumerate(self.fields):
            item = qg.QStandardItem(field)
            item.setData(i, qc.Qt.ItemDataRole.UserRole)
            item.setDragEnabled(True)
            item.setCheckable(True)
            item.setCheckState(qc.Qt.CheckState.Checked)
            self.appendRow(item)

    def checked_fields(self):
        return [
            self.item(i).text()
            for i in range(self.rowCount())
            if self.item(i).checkState() == qc.Qt.CheckState.Checked
        ]
