import PySide6.QtWidgets as qw

import datalake as dl


class ImmunoExplorer(qw.QWidget):

    def __init__(self, datalake: dl.DataLake, parent=None):
        super().__init__(parent)

        self._layout = qw.QVBoxLayout()

        self.datalake = datalake
        self.query = self.datalake.get_query("validation")

        self.setLayout(self._layout)
