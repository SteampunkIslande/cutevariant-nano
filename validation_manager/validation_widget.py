from pathlib import Path

import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

import app as ap
import datalake.datalake_component as dl_cmp
import query_manager.query_manager_component as qm
from commons import yaml_load


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

    def export_csv(self):
        user_prefs = self.app.load_user_prefs()
        if "genno_export_folder" not in user_prefs:
            qw.QMessageBox.warning(
                self,
                self.app.translate("Export"),
                self.app.translate(
                    "No Genno export folder selected, please choose one."
                ),
            )
            genno_export_folder = qw.QFileDialog.getExistingDirectory(
                self, self.app.translate("Choose Genno export folder")
            )
            if genno_export_folder:
                self.app.save_user_prefs({"genno_export_folder": genno_export_folder})
            else:
                qw.QMessageBox.warning(
                    self,
                    self.app.translate("Export"),
                    self.app.translate("No Genno export folder selected, aborting."),
                )
                return
        else:
            genno_export_folder = user_prefs["genno_export_folder"]

        genno_export_folder = Path(genno_export_folder)

        # Now, export final CSV to Genno

        final_query = self.query.select_query(
            paginated=False, columns="COLUMNS('^[^.].+$')"
        )
        conn = self.datalake.get_database("validation")
        conn.sql(
            f"COPY ({final_query}) TO '{genno_export_folder / self.validation_name}.csv' (FORMAT CSV, HEADER, SEPARATOR ';')"
        )
        conn.close()

    def set_method_path(self, method_path: Path):
        if not method_path.exists():
            qw.QMessageBox.critical(
                self,
                self.app.translate("Error"),
                self.app.translate("Method file {method_path} doesn't exist.").format(
                    method_path=method_path
                ),
            )
            return
        self.method: dict = yaml_load(method_path)

    def start_validation(self, selected_validation: dict):
        if not self.datalake:
            return

        succes, config_folder = self.app.get_config_folder()
        if not succes:
            return

        self.validation_name = selected_validation["validation_name"]
        self.validation_parquet_files = selected_validation["parquet_files"]
        self.validation_table_uuid = selected_validation["table_uuid"]
        self.validation_sample_names = selected_validation["sample_names"]
        self.validation_gene_names = selected_validation["gene_names"]

        self.set_method_path(
            config_folder
            / "validation_methods"
            / (selected_validation["validation_method"] + ".yaml")
        )

        try:
            self.completed = self.datalake.run_with_connection(
                "validation",
                lambda conn: conn.sql(
                    f"SELECT completed FROM validations WHERE table_uuid = '{self.validation_table_uuid}'"
                )
                .pl()
                .to_dicts()[0]["completed"],
            )
            if self.completed:
                self.validate_button.setText(self.app.translate("Export to Genno"))
                step_definition = self.method["final"]["query"]
                # Hint: Emit a signal to tell to show the final query

            else:
                self.step_selection_list_view.selectionModel().setCurrentIndex(
                    self.step_model.index(0),
                    qc.QItemSelectionModel.SelectionFlag.Select,
                )
                # Make sure the selection list view is visible
                self.step_selection_list_view.show()
        except IndexError:
            print(self.validation_table_uuid)
