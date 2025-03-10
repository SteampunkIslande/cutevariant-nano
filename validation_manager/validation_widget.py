import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

import app as ap
import datalake.datalake_component as dl_cmp
import query_manager.query_manager_component as qm


class ValidationWidget(qw.QWidget):

    validate = qc.Signal()

    return_to_validation = qc.Signal()

    def __init__(
        self,
        app: ap.App,
        query_manager: qm.QueryManagerComponent,
        datalake: dl_cmp.Datalake,
        parent: qw.QWidget = None,
    ):
        super().__init__(parent)

        self._layout = qw.QVBoxLayout(self)

        self.app = app
        self.datalake = datalake

        self.validate_button = qw.QPushButton(self.app.translate("Validate cart"), self)
        self.validate_button.clicked.connect(self.on_validate)

        self.return_to_validation_button = qw.QPushButton(
            self.app.translate("Back to validation selection"), self
        )

        self.return_to_validation_button.clicked.connect(self.on_return_to_validation)

        self.query_manager_widget = query_manager.widget()

        self.setup_layout()

    def setup_layout(self):

        self._layout.addWidget(self.query_manager_widget)
        # Add vertical spacer
        self._layout.addStretch()

        self._layout.addWidget(self.validate_button)
        self._layout.addWidget(self.return_to_validation_button)
        self.setLayout(self._layout)

    def on_validate(self):
        self.completed = True

        self.validate.emit()

    def on_return_to_validation(self):
        self.return_to_validation.emit()
