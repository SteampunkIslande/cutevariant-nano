# A simple PySide6 QTableModel, displaying key value pairs


import PySide6.QtCore as qc

import query as q


class VariantValidationModel(qc.QAbstractTableModel):
    def __init__(self, query: "q.Query", parent=None):
        super().__init__(parent)
        self.query = query
        self._data = []

    def load(self, variant_hash: int):
        # self._data = self.query.get
        # self.layoutChanged.emit()
        pass
