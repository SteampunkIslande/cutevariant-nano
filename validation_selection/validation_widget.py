from pathlib import Path

import PySide6.QtCore as qc
import PySide6.QtWidgets as qw
from validation_model import ValidationModel
from validation_wizard import ValidationWizard

import datalake.datalake_component as dl
from common_widgets.searchable_table import SearchableTable
from commons import get_config_folder

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


class ValidationWelcomeWidget(qw.QWidget):

    validation_start = qc.Signal()

    def __init__(self, datalake: dl.Datalake, parent=None):
        super().__init__(parent)
        self.datalake = datalake
        self.model = ValidationModel(self.datalake, self)

        self._layout = qw.QVBoxLayout(self)

        self.new_validation_button = qw.QPushButton(
            qc.QCoreApplication.tr("Nouvelle validation"), self
        )
        self.new_validation_button.clicked.connect(self.on_new_validation_clicked)

        self.start_validation_button = qw.QPushButton(
            qc.QCoreApplication.tr("Démarrer/Continuer une validation"), self
        )
        self.start_validation_button.clicked.connect(self.on_start_validation_clicked)

        if not self.datalake.datalake_path:
            self.new_validation_button.setEnabled(False)
            self.start_validation_button.setEnabled(False)

        self.datalake.folder_changed.connect(self.on_datalake_changed)

        self.table = SearchableTable(self.model, parent=self)
        self.hide_unwanted_columns()

        self.init_layout()

    def hide_unwanted_columns(self):
        self.table.view.hideColumn(VALIDATION_TABLE_COLUMNS["table_uuid"])

    def on_new_validation_clicked(self):
        if not self.datalake:
            return
        username = Path.home().name

        # Make sure we have a config folder (before we start the wizard)
        success, _ = get_config_folder()
        if not success:
            qw.QMessageBox.critical(
                self,
                qc.QCoreApplication.tr("Erreur"),
                qc.QCoreApplication.tr(
                    "Pas de dossier de configuration sélectionné, abandon."
                ),
            )
            return

        wizard = ValidationWizard(self.datalake, self)
        if wizard.exec() == qw.QDialog.DialogCode.Accepted:

            self.model.new_validation(username=username, **wizard.data)

    def on_start_validation_clicked(self):
        selected_validation = self.get_selected_validation()
        if selected_validation:
            self.validation_start.emit()
        else:
            qw.QMessageBox.warning(
                self,
                qc.QCoreApplication.tr("Validation"),
                qc.QCoreApplication.tr(
                    "Veuillez sélectionner une validation à exécuter."
                ),
            )

    def init_layout(self):
        self._layout.addWidget(self.table)
        self._layout.addWidget(self.new_validation_button)
        self._layout.addWidget(self.start_validation_button)
        self.setLayout(self._layout)

    def on_datalake_changed(self):
        self.model.update()
        self.hide_unwanted_columns()
        if self.datalake and self.datalake.datalake_path:
            self.new_validation_button.setEnabled(True)
            self.start_validation_button.setEnabled(True)

    def get_selected_validation(self):
        selected = self.table.view.selectionModel().selectedRows()
        if selected:
            return selected[0].data(qc.Qt.ItemDataRole.UserRole)
        return None
