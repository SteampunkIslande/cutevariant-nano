from pathlib import Path

import duckdb as db
import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

import app as ap

from commons import get_config_folder, load_user_prefs, save_user_prefs, yaml_load


def finish_validation(conn: db.DuckDBPyConnection, table_uuid: str):
    conn.sql(
        f"UPDATE validations SET completed = TRUE WHERE table_uuid = '{table_uuid}'"
    )


class ValidationManagerWidget(qw.QWidget):

    return_to_validation = qc.Signal()

    def __init__(self, parent: qw.QWidget = None):
        super().__init__(parent)

        self._layout = qw.QVBoxLayout(self)

        self.validate_button = qw.QPushButton("", self)
        self.validate_button.clicked.connect(self.validate)

        self.return_to_validation_button = qw.QPushButton("", self)

        self.return_to_validation_button.clicked.connect(self.on_return_to_validation)

        # Will be overwritten by load_state, but set to default values here in case load_state does nothing
        self.init_state()

        self.setup_layout()

    def setup_layout(self):

        # Add vertical spacer
        self._layout.addStretch()

        self._layout.addWidget(self.validate_button)
        self._layout.addWidget(self.return_to_validation_button)
        self.setLayout(self._layout)

    def init_state(self):

        # The table uuid of the selected validation
        self.validation_table_uuid = None
        self.validation_name = None
        self.validation_parquet_files = None
        self.validation_sample_names = None
        self.validation_gene_names = None

        self.validate_button.setText(qc.QCoreApplication.tr("Valider le panier"))
        self.return_to_validation_button.setText(
            qc.QCoreApplication.tr("Retour à la sélection des validations")
        )

        self.completed = False

    def validate(self):
        conn = self.datalake.get_database("validation")
        try:
            self.export_csv()
            finish_validation(conn, self.validation_table_uuid)
            self.completed = True
            step_definition = self.method["final"]["query"]
            self.setup_step(step_definition)
        except Exception as e:
            print(e)
        finally:
            conn.close()

    def on_return_to_validation(self):
        self.init_state()
        self.return_to_validation.emit()

    def export_csv(self):
        user_prefs = load_user_prefs()
        if "genno_export_folder" not in user_prefs:
            qw.QMessageBox.warning(
                self,
                qc.QCoreApplication.tr("Export"),
                qc.QCoreApplication.tr(
                    "Pas de dossier d'export Genno sélectionné, veuillez en choisir un."
                ),
            )
            genno_export_folder = qw.QFileDialog.getExistingDirectory(
                self, qc.QCoreApplication.tr("Choisir le dossier d'export Genno")
            )
            if genno_export_folder:
                save_user_prefs({"genno_export_folder": genno_export_folder})
            else:
                qw.QMessageBox.warning(
                    self,
                    qc.QCoreApplication.tr("Export"),
                    qc.QCoreApplication.tr(
                        "Pas de dossier d'export Genno sélectionné. Abandon."
                    ),
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
                qc.QCoreApplication.tr("Erreur"),
                qc.QCoreApplication.tr(
                    "Le fichier de méthode {method_path} n'existe pas.".format(
                        method_path=method_path
                    )
                ),
            )
            return
        self.method: dict = yaml_load(method_path)
        self.step_model.set_steps(self.method["steps"])
        self.method_changed.emit()

    def update_step(self, index: qc.QModelIndex):
        self.current_step_id = index.row()
        step_definition = index.data(qc.Qt.ItemDataRole.UserRole)
        self.setup_step(step_definition)

    def setup_step(self, step_definition: dict):
        """Modifies the query to match the current step definition."""
        if (
            not self.validation_name
            or not self.validation_parquet_files
            or not self.method
            or not self.datalake
            or not self.query
        ):
            return

        self.query.set_readonly_table(
            self.validation_parquet_files
        ).set_editable_table_name(self.validation_table_uuid).set_selected_genes(
            self.validation_gene_names
        ).set_selected_samples(
            self.validation_sample_names
        ).setup_query(
            step_definition
        ).commit()

    def start_validation(self, selected_validation: dict):
        if not self.datalake:
            return

        succes, config_folder = get_config_folder()
        if not succes:
            qw.QMessageBox.critical(
                self,
                qc.QCoreApplication.tr("Erreur"),
                qc.QCoreApplication.tr(
                    "Pas de dossier de configuration sélectionné, abandon."
                ),
            )
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
        conn = self.datalake.get_database("validation")

        # Might be a good place to load previous step ID

        self.step_selection_list_view.selectionModel().setCurrentIndex(
            self.step_model.index(self.current_step_id),
            qc.QItemSelectionModel.SelectionFlag.Select,
        )

        try:
            self.completed = (
                conn.sql(
                    f"SELECT completed FROM validations WHERE table_uuid = '{self.validation_table_uuid}'"
                )
                .pl()
                .to_dicts()[0]["completed"]
            )
            if self.completed:
                self.validate_button.setText(
                    qc.QCoreApplication.tr("Exporter vers Genno")
                )
                step_definition = self.method["final"]["query"]
                self.setup_step(step_definition)

                # Hide the selection list view
                self.step_selection_list_view.hide()
            else:
                self.step_selection_list_view.selectionModel().setCurrentIndex(
                    self.step_model.index(0),
                    qc.QItemSelectionModel.SelectionFlag.Select,
                )
                # Make sure the selection list view is visible
                self.step_selection_list_view.show()
        except IndexError:
            print(self.validation_table_uuid)
        finally:
            conn.close()


class ValidationManagerComponent(ap.AppComponent):

    pass
