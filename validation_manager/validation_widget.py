import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

import app as ap
import query_manager.query_manager_component as qmc
import validation_manager.validation_manager_component as vmc


class ValidationWidget(qw.QWidget):

    validate = qc.Signal()
    export_to_genno = qc.Signal()
    return_to_validation = qc.Signal()

    def __init__(
        self,
        app: ap.App,
        parent_component: "vmc.ValidationManagerComponent",
        parent: qw.QWidget = None,
    ):
        super().__init__(parent)

        self.parent_component = parent_component
        self.parent_component.closing.connect(self.on_parent_component_closing)
        self._layout = qw.QVBoxLayout(self)
        self.app = app

        self.query_manager: qmc.QueryManagerComponent = self.app.get_component(
            "query_manager"
        )

        self.validate_button = qw.QPushButton(self.app.translate("Validate cart"), self)

        self.return_to_validation_button = qw.QPushButton(
            self.app.translate("Back to validation selection"), self
        )

        self.return_to_validation_button.clicked.connect(self.on_return_to_validation)

        self.query_manager_widget = self.query_manager.widget()
        self.query_manager.closing.connect(self.on_query_manager_closing)

        self.setup_layout()

        self.completed = False
        self.setup_state()

    def on_query_manager_closing(self):
        self.query_manager_widget = None
        self.query_manager = None

    def setup_layout(self):
        self._layout.addWidget(self.query_manager_widget)

        # FIX: Ensure widget visibility after adding to layout
        # Widget may lose visibility state during reparenting
        self.query_manager_widget.show()

        # Add vertical spacer
        self._layout.addStretch()

        self._layout.addWidget(self.validate_button)
        self._layout.addWidget(self.return_to_validation_button)
        self.setLayout(self._layout)

    def set_completed(self, completed: bool):
        self.completed = completed
        self.setup_state()

    def setup_state(self):
        if self.completed:
            self.validate_button.setText(self.app.translate("Export to Genno"))
            if self.validate_button.isSignalConnected(
                qc.QMetaMethod.fromSignal(self.validate_button.clicked)
            ):
                self.validate_button.clicked.disconnect(self.on_validate)
            self.validate_button.clicked.connect(self.on_export_to_genno)
        else:
            self.validate_button.setText(self.app.translate("Validate cart"))
            if self.validate_button.isSignalConnected(
                qc.QMetaMethod.fromSignal(self.validate_button.clicked)
            ):
                self.validate_button.clicked.disconnect(self.on_export_to_genno)
            self.validate_button.clicked.connect(self.on_validate)

    def on_validate(self):
        self.completed = True
        self.setup_state()
        self.validate.emit()

    def on_export_to_genno(self):
        self.export_to_genno.emit()

    def on_return_to_validation(self):
        self.completed = False
        self.setup_state()
        self.return_to_validation.emit()

    def on_parent_component_closing(self):
        self.app = None
        self.parent_component = None
        self._layout = None
        self.validate_button = None
        self.return_to_validation_button = None
        self.query_manager_widget = None
