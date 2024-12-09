# A simple PySide6 QTableModel, displaying key value pairs


import PySide6.QtCore as qc


class VariantValidationModel(qc.QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = {}
