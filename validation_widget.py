import json
from pathlib import Path

import duckdb as db
import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

import datalake as dl
from common_widgets.multiline_display import MultiLineDisplay
from common_widgets.multiwidget_holder import MultiWidgetHolder
from common_widgets.searchable_table import SearchableTable
from commons import get_config_folder, load_user_prefs, save_user_prefs
from validation_model import (
    VALIDATION_TABLE_COLUMNS,
    ValidationModel,
    get_validation_from_table_uuid,
)
from validation_wizard import ValidationWizard


def finish_validation(conn: db.DuckDBPyConnection, table_uuid: str, step_count: int):
    conn.sql(
        f"UPDATE validations SET last_step = {step_count} WHERE table_uuid = '{table_uuid}'"
    )
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
        userprefs = load_user_prefs()
        if "config_folder" not in userprefs:
            qw.QMessageBox.warning(
                self,
                qc.QCoreApplication.tr("Validation"),
                qc.QCoreApplication.tr(
                    "Pas de dossier de configuration trouvé, veuillez en choisir un."
                ),
            )
            config_folder = qw.QFileDialog.getExistingDirectory(
                self,
                qc.QCoreApplication.tr(
                    "Pas de dossier de configuration trouvé, veuillez en choisir un."
                ),
            )
            if config_folder:
                # config_folder will be read by the wizard
                save_user_prefs({"config_folder": config_folder})
            else:
                return

        wizard = ValidationWizard(self.datalake, self)
        if wizard.exec() == qw.QDialog.DialogCode.Accepted:
            file_names = wizard.data["file_names"]
            sample_names = wizard.data["sample_names"]
            genes_list = wizard.data["genes_list"]
            validation_name = wizard.data["validation_name"]
            validation_method = wizard.data["validation_method"]
            if "config_folder" not in userprefs:
                return

            config_folder = Path(userprefs["config_folder"])

            self.model.new_validation(
                validation_name, username, file_names, sample_names, validation_method
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


class ValidationWidget(qw.QWidget):

    return_to_validation = qc.Signal()

    def __init__(self, datalake: dl.DataLake, parent=None):
        super().__init__(parent)
        self.datalake = datalake
        self.query = self.datalake.get_query("validation")

        self._layout = qw.QVBoxLayout(self)

        self.title_label = qw.QLabel("")
        self.description_text = MultiLineDisplay(self)

        self.next_step_button = qw.QPushButton("", self)
        self.next_step_button.clicked.connect(self.on_next_step_clicked)

        self.return_to_validation_button = qw.QPushButton("", self)

        self.return_to_validation_button.clicked.connect(self.on_return_to_validation)

        # Will be overwritten by load_state, but set to default values here in case load_state does nothing
        self.init_state()

        self.setup_layout()

    def setup_layout(self):
        self._layout.addWidget(self.title_label)
        self._layout.addWidget(self.description_text)

        # Add vertical spacer
        self._layout.addStretch()

        self._layout.addWidget(self.next_step_button)
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

        self.next_step_button.setText(qc.QCoreApplication.tr("Prochaine étape"))
        self.return_to_validation_button.setText(
            qc.QCoreApplication.tr("Retour à la sélection des validations")
        )

        self.is_finished = False

    def on_finish(self):
        if self.is_finished:
            return

        self.is_finished = True
        self.title_label.setText(qc.QCoreApplication.tr("Validation terminée"))
        self.description_text.text_edit.setText(
            qc.QCoreApplication.tr(
                "Validation terminée.\nLes résultats sont présentés dans la table ci-contre.\nVous pouvez exporter ces résultats vers Genno en cliquant sur le bouton ci-dessous."
            )
        )
        self.next_step_button.setText(qc.QCoreApplication.tr("Exporter vers Genno"))

        conn = self.datalake.get_database("validation")

        validation = get_validation_from_table_uuid(conn, self.validation_table_uuid)
        if not validation:
            return

        parquet_files = validation["parquet_files"]
        validation_name = validation["validation_name"]
        conn.close()

        last_step_definition = self.method["final"]

        self.query.mute().set_readonly_table(parquet_files).set_editable_table_name(
            self.validation_table_uuid
        ).unmute().generate_query_template_from_json(last_step_definition["query"])

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

    def on_next_step_clicked(self):
        # Export to genno
        if self.is_finished:
            self.export_csv()
            return

        # Decide whether we continue or if we reached the end
        if self.current_step_id < len(self.method["steps"]):
            self.setup_step()
            # Increment the step index
            self.current_step_id += 1
            return
        else:
            self.on_finish()

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
        with open(method_path, "r") as f:
            self.method = json.load(f)

    def setup_step(self):
        """Modifies the query to match the current step definition."""
        if (
            not self.validation_name
            or not self.validation_parquet_files
            or not self.method
            or not self.datalake
            or self.current_step_id >= len(self.method["steps"])
            or self.current_step_id < 0
        ):
            return

        step_definition = self.method["steps"][self.current_step_id]

        self.title_label.setText(step_definition["title"])
        self.description_text.text_edit.setText(step_definition["description"])

        self.query.mute().set_readonly_table(
            self.validation_parquet_files
        ).set_editable_table_name(
            self.validation_table_uuid
        ).unmute().generate_query_template_from_json(
            step_definition["query"]
        )

    def start_validation(self, selected_validation: dict):
        if not self.datalake:
            return

        config_folder = get_config_folder()
        if not config_folder:
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

        self.set_method_path(
            Path(config_folder)
            / "validation_methods"
            / (selected_validation["validation_method"] + ".json")
        )
        try:
            conn = self.datalake.get_database("validation")
            self.current_step_id = (
                conn.sql(f"SELECT last_step FROM validations WHERE table_uuid = '{self.validation_table_uuid}'").pl().to_dicts()[0]["last_step"]
            )
            self.completed = (
                conn.sql(f"SELECT last_step FROM validations WHERE table_uuid = '{self.validation_table_uuid}'").pl().to_dicts()[0]["completed"]
            )
            if self.current_step_id >= len(self.method["steps"]):
                self.on_finish()
            else:
                self.setup_step()
        except IndexError:
            self.current_step_id = 0
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
        if not config_folder:
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
