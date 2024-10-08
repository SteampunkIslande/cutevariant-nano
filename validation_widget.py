from pathlib import Path
from typing import List

import duckdb as db
import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

import datalake as dl
from common_widgets.multiwidget_holder import MultiWidgetHolder
from common_widgets.searchable_table import SearchableTable
from commons import get_config_folder, load_user_prefs, save_user_prefs, yaml_load
from validation_model import VALIDATION_TABLE_COLUMNS, ValidationModel
from validation_wizard import ValidationWizard


def finish_validation(conn: db.DuckDBPyConnection, table_uuid: str):
    conn.sql(
        f"UPDATE validations SET completed = TRUE WHERE table_uuid = '{table_uuid}'"
    )


class ValidationWelcomeWidget(qw.QWidget):

    validation_start = qc.Signal()

    def __init__(self, datalake: dl.DataLake, parent=None):
        super().__init__(parent)
        self.datalake = datalake
        self.model = ValidationModel(self.datalake, self)
        self.query = self.datalake.get_query("validation")

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
        config_folder = get_config_folder()
        if not config_folder.is_dir():
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
            file_names = wizard.data["file_names"]
            sample_names = wizard.data["sample_names"]
            genes_list = wizard.data["gene_names"]
            validation_name = wizard.data["validation_name"]
            validation_method = wizard.data["validation_method"]

            self.model.new_validation(
                validation_name,
                username,
                file_names,
                sample_names,
                genes_list,
                validation_method,
            )

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


class StepModel(qc.QAbstractListModel):

    def __init__(self, steps: List[dict], parent=None):
        super().__init__(parent)
        self.steps = steps

    def rowCount(self, parent: qc.QModelIndex):
        if parent.isValid():
            return 0
        return len(self.steps)

    def columnCount(self, parent: qc.QModelIndex):
        if parent.isValid():
            return 0
        return 1

    def data(self, index: qc.QModelIndex, role: int):
        if not index.isValid():
            return None
        if role == qc.Qt.ItemDataRole.DisplayRole:
            return self.steps[index.row()]["title"]
        if role == qc.Qt.ItemDataRole.ToolTipRole:
            return self.steps[index.row()]["description"]
        if role == qc.Qt.ItemDataRole.UserRole:
            return self.steps[index.row()]["query"]
        return None

    def headerData(self, section: int, orientation: qc.Qt.Orientation, role: int):
        if (
            orientation == qc.Qt.Orientation.Horizontal
            and role == qc.Qt.ItemDataRole.DisplayRole
            and section == 0
        ):
            return "Steps"
        return None

    def set_steps(self, steps):
        self.beginResetModel()
        self.steps = steps
        self.endResetModel()

    def flags(self, index: qc.QModelIndex):
        return qc.Qt.ItemFlag.ItemIsSelectable | qc.Qt.ItemFlag.ItemIsEnabled


class ValidationWidget(qw.QWidget):

    return_to_validation = qc.Signal()

    def __init__(self, datalake: dl.DataLake, parent=None):
        super().__init__(parent)
        self.datalake = datalake
        self.query = self.datalake.get_query("validation")

        self._layout = qw.QVBoxLayout(self)

        self.step_model = StepModel([], self)
        self.step_selection_list_view = qw.QListView(self)

        self.step_selection_list_view.setModel(self.step_model)
        self.step_selection_list_view.setSelectionMode(
            qw.QAbstractItemView.SelectionMode.SingleSelection
        )

        self.step_selection_list_view.selectionModel().currentChanged.connect(
            self.update_step
        )

        self.validate_button = qw.QPushButton("", self)
        self.validate_button.clicked.connect(self.validate)

        self.return_to_validation_button = qw.QPushButton("", self)

        self.return_to_validation_button.clicked.connect(self.on_return_to_validation)

        # Will be overwritten by load_state, but set to default values here in case load_state does nothing
        self.init_state()

        self.setup_layout()

    def setup_layout(self):

        self._layout.addWidget(self.step_selection_list_view)
        # Add vertical spacer
        self._layout.addStretch()

        self._layout.addWidget(self.validate_button)
        self._layout.addWidget(self.return_to_validation_button)
        self.setLayout(self._layout)

    def init_state(self):

        # The current step index
        self.current_step_id = 0

        # The method array (a list of steps, each step being a dict with fields, tables, joins, etc.)
        self.method = None

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
        if not self.datalake:
            # WTF ? This should never happen
            return
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

        final_query = self.query.select_query(paginated=False)
        db.sql(
            f"COPY ({final_query}) TO '{genno_export_folder / self.validation_name}.csv' (FORMAT CSV, HEADER)"
        )

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
        self.method = yaml_load(method_path)
        self.step_model.set_steps(self.method["steps"])

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
        ).generate_query_template_from_json(
            step_definition
        ).commit()

    def start_validation(self, selected_validation: dict):
        if not self.datalake:
            return

        config_folder = get_config_folder()
        if not config_folder.is_dir():
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
            Path(config_folder)
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


class ValidationWidgetContainer(qw.QWidget):

    def __init__(self, datalake: dl.DataLake, parent=None):
        super().__init__(parent)
        self.datalake = datalake

        self._layout = qw.QVBoxLayout(self)

        self.validation_welcome_widget = ValidationWelcomeWidget(self.datalake, self)
        self.validation_welcome_widget.validation_start.connect(
            self.on_validation_start
        )

        self.validation_widget = ValidationWidget(self.datalake, self)
        self.validation_widget.return_to_validation.connect(
            self.on_return_to_validation
        )

        self.multi_widget = MultiWidgetHolder(self)
        self.multi_widget.add_widget(self.validation_welcome_widget, "welcome")
        self.multi_widget.add_widget(self.validation_widget, "validation")

        self.multi_widget.set_current_widget("welcome")

        self._layout.addWidget(self.multi_widget)

        qc.QCoreApplication.instance().aboutToQuit.connect(self.on_close)

        # Don't load previous session for now
        # self.load_previous_session()

        self.validation_query = self.datalake.get_query("validation")

        self.setLayout(self._layout)

    def on_validation_start(self):
        if not self.validation_welcome_widget.get_selected_validation():
            return
        self.multi_widget.set_current_widget("validation")
        self.validation_widget.init_state()

        config_folder = get_config_folder()
        if not config_folder.is_dir():
            qw.QMessageBox.critical(
                self,
                qc.QCoreApplication.tr("Erreur"),
                qc.QCoreApplication.tr(
                    "Pas de dossier de configuration sélectionné, abandon."
                ),
            )
            return

        selected_validation = self.validation_welcome_widget.get_selected_validation()

        self.validation_widget.start_validation(selected_validation)

    def on_return_to_validation(self):
        self.multi_widget.set_current_widget("welcome")
        self.validation_widget.init_state()
        self.validation_welcome_widget.model.update()

        self.validation_query.init_state()

    def load_previous_session(self):
        userprefs = load_user_prefs()
        if "last_widget_shown" in userprefs:
            self.multi_widget.set_current_widget(userprefs["last_widget_shown"])

    def on_close(self):
        save_user_prefs(
            {"last_widget_shown": self.multi_widget.get_current_widget_name()}
        )
