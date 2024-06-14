import PySide6.QtWidgets as qw

from datalake import DataLake
from validation_widget import ValidationWidgetContainer


class Inspector(qw.QWidget):

    def __init__(self, datalake: DataLake, parent=None):
        super().__init__(parent)

        self._layout = qw.QVBoxLayout()

        self.datalake = datalake

        self.main_widget = qw.QTabWidget()
        self._layout.addWidget(self.main_widget)

        self.tabs = {}

        self.setLayout(self._layout)

        self.setup()

    def setup(self):
        self.validation_widget = ValidationWidgetContainer(self.datalake)
        self.main_widget.addTab(self.validation_widget, "Validation")
        self.tabs["validation"] = self.validation_widget
