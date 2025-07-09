import os
from pathlib import Path

import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

import app as ap
import validation_manager.validation_manager_component as vmc
from common_widgets.smart_view import SmartView
from validation_manager.validation_model import ValidationModel
from validation_manager.validation_wizard import ValidationWizard

VALIDATION_TABLE_COLUMNS = {
    v: i
    for i, v in enumerate(
        [
            "parquet_files",
            "sample_names",
            "gene_names",
            "username",
            "validation_name",
            "table_uuid",
            "creation_date",
            "completed",
            "last_step",
        ]
    )
}


class ValidationSelectionWidget(qw.QWidget):

    validation_start = qc.Signal()

    def __init__(
        self,
        app: ap.App,
        validation_model: ValidationModel,
        parent_component: ap.AppComponent,
        parent=None,
    ):
        super().__init__(parent)
        self.app = app
        self.parent_component: vmc.ValidationManagerComponent = parent_component
        self.model = validation_model

        self._layout = qw.QVBoxLayout(self)

        self.show_completed_checkbox = qw.QCheckBox(
            self.app.translate("Hide completed validations?"), self
        )
        self.show_completed_checkbox.toggled.connect(self.model.set_hide_completed)
        self.view = SmartView(self.model, parent=self)
        self.view.filter_le.setPlaceholderText(
            self.app.translate("Filter on validation name...")
        )
        self.model.model_updated.connect(
            lambda: self.view.set_list_view_column(
                VALIDATION_TABLE_COLUMNS["validation_name"]
            )
        )

        self.new_validation_button = qw.QPushButton(
            self.app.translate("New validation"), self
        )
        self.new_validation_button.clicked.connect(self.on_new_validation_clicked)

        self.start_validation_button = qw.QPushButton(
            self.app.translate("Start/Resume validation"), self
        )
        self.start_validation_button.clicked.connect(self.on_start_validation_clicked)

        if not self.parent_component.get_datalake():
            self.new_validation_button.setEnabled(False)
            self.start_validation_button.setEnabled(False)

        # self.datalake.folder_changed.connect(self.on_datalake_changed)

        self.init_layout()

    def on_new_validation_clicked(self):
        datalake = self.parent_component.get_datalake()
        if not datalake:
            return
        username = Path.home().name

        # Make sure we have a config folder (before we start the wizard)
        success = self.app.ensure_config_folder()
        if not success:
            qw.QMessageBox.critical(
                self,
                self.app.translate("Error"),
                self.app.translate("No configuration folder defined, aborting."),
            )
            return

        wizard = ValidationWizard(self.app, datalake, self)
        if wizard.exec() == qw.QDialog.DialogCode.Accepted:

            self.model.new_validation(username=username, **wizard.data)

    def on_start_validation_clicked(self):
        selected_validation = self.get_selected_validation()
        if selected_validation:
            self.validation_start.emit()
        else:
            qw.QMessageBox.warning(
                self,
                self.app.translate("No validation selected"),
                self.app.translate("Please select a validation."),
            )

    def init_layout(self):
        self._layout.addWidget(self.show_completed_checkbox)
        self._layout.addWidget(self.view)
        self._layout.addWidget(self.new_validation_button)
        self._layout.addWidget(self.start_validation_button)
        self.setLayout(self._layout)
        # Load initial data
        if self.parent_component.get_datalake():
            self.model.update()

    def on_datalake_changed(self):
        datalake = self.parent_component.get_datalake()
        if (
            datalake
            and datalake.datalake_path
            and os.path.exists(datalake.datalake_path)
        ):
            self.new_validation_button.setEnabled(True)
            self.start_validation_button.setEnabled(True)
            self.model.update()

    def get_selected_validation(self) -> dict:
        selected = self.view.list_view.selectionModel().selectedIndexes()
        if selected:
            return selected[0].data(qc.Qt.ItemDataRole.UserRole)
        return None
