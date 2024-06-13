import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

from commons import load_user_prefs, save_user_prefs
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

        qc.QCoreApplication.instance().aboutToQuit.connect(self.on_close)

        self.setup()

    def setup(self):
        self.validation_widget = ValidationWidgetContainer(self.datalake)
        self.main_widget.addTab(self.validation_widget, "Validation")
        self.tabs["validation"] = self.validation_widget

        user_prefs = load_user_prefs()

        if user_prefs.get("inspector_tab") is not None:
            self.main_widget.setCurrentIndex(user_prefs["inspector_tab"])

    def on_close(self):
        save_user_prefs({"inspector_tab": self.main_widget.currentIndex()})
