# A model to selected fields using checkboxes


import PySide6.QtCore as qc
import PySide6.QtGui as qg


class FieldsModel(qg.QStandardItemModel):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.fields = []

    def update_fields(self, fields: list[str]):
        self.fields = fields
        self.load()

    def load(self):
        self.clear()
        if not self.fields:
            return
        for i, field in enumerate(self.fields):
            item = qg.QStandardItem(field)
            # item.setData(i, qc.Qt.ItemDataRole.UserRole)
            item.setDragEnabled(True)
            item.setCheckable(True)
            item.setCheckState(qc.Qt.CheckState.Checked)
            self.appendRow(item)

    def canDropMimeData(self, data, action, row, column, parent):
        if parent.isValid():
            return False
        return True

    def set_checked_fields(self, fields: list[str]):
        for i in range(self.rowCount()):
            item = self.item(i)
            item.setCheckState(
                qc.Qt.CheckState.Checked
                if item.text() in fields
                else qc.Qt.CheckState.Unchecked
            )

    def checked_fields(self):
        return [
            self.item(i).text()
            for i in range(self.rowCount())
            if self.item(i).checkState() == qc.Qt.CheckState.Checked
        ]
