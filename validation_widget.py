import json
from pathlib import Path
from typing import List

import duckdb as db
import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

from common_widgets.any_widget_dialog import AnyWidgetDialog
from common_widgets.multiline_display import MultiLineDisplay
from common_widgets.multiwidget_holder import MultiWidgetHolder
from common_widgets.searchable_table import SearchableTable
from common_widgets.string_list_chooser import StringListChooser
from commons import (
    duck_db_literal_string_list,
    get_config_folder,
    load_user_prefs,
    save_user_prefs,
)
from datalake import DataLake, get_database
from validation_model import (
    VALIDATION_TABLE_COLUMNS,
    ValidationModel,
    get_validation_from_table_uuid,
)


def finish_validation(conn: db.DuckDBPyConnection, table_uuid: str, step_count: int):
    conn.sql(
        f"UPDATE validations SET last_step = {step_count} WHERE table_uuid = '{table_uuid}'"
    )
    conn.sql(
        f"UPDATE validations SET completed = TRUE WHERE table_uuid = '{table_uuid}'"
    )


def show_finished_validation(full_database_path: Path, table_uuid: str):

    if full_database_path.exists() and table_uuid:
        conn = get_database(full_database_path)

        validation = get_validation_from_table_uuid(conn, table_uuid)
        if not validation:
            return


class ValidationWelcomeWidget(qw.QWidget):

    validation_start = qc.Signal()

    def __init__(self, datalake: DataLake, parent=None):
        super().__init__(parent)
        self.datalake = datalake
        self.model = ValidationModel(self.datalake, self)
        self.query = self.datalake.get_query("validation")

        self._layout = qw.QVBoxLayout(self)

        self.new_validation_button = qw.QPushButton("New Validation", self)
        self.new_validation_button.clicked.connect(self.on_new_validation_clicked)

        self.start_validation_button = qw.QPushButton("Start Validation", self)
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
                "Validation",
                "Pas de dossier de configuration trouvé, veuillez en choisir un.",
            )
            config_folder = qw.QFileDialog.getExistingDirectory(
                self, "Pas de dossier de configuration trouvé, veuillez en choisir un."
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
                self, "Validation", "Veuillez sélectionner une validation à exécuter."
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

    def __init__(self, datalake: DataLake, parent=None):
        super().__init__(parent)
        self.datalake = datalake
        self.query = self.datalake.get_query("validation")

        self._layout = qw.QVBoxLayout(self)

        self.title_label = qw.QLabel("")
        self.description_text = MultiLineDisplay(self)

        self.next_step_button = qw.QPushButton("Next Step", self)
        self.next_step_button.clicked.connect(self.on_next_step_clicked)

        self.return_to_validation_button = qw.QPushButton(
            "Back to validation selection", self
        )

        self.return_to_validation_button.clicked.connect(self.on_return_to_validation)

        qc.QCoreApplication.instance().aboutToQuit.connect(self.save_state)

        # Will be overwritten by load_state, but set to default values here in case load_state does nothing
        self.init_state()
        # self.load_state()

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

        self.next_step_button.setText("Next Step")
        self.return_to_validation_button.setText("Back to validation selection")

        self.is_finished = False

    def on_finish(self):
        self.is_finished = True
        self.title_label.setText("Validation terminée")
        self.description_text.text_edit.setText(
            "Validation terminée.\nLes résultats sont présentés dans la table ci-contre.\nVous pouvez exporter les résultats vers Genno en cliquant sur le bouton ci-dessous."
        )

        finish_validation(
            self.datalake.conn, self.validation_table_uuid, len(self.method)
        )
        show_finished_validation(self.datalake, self.validation_table_uuid)
        self.next_step_button.setText("Export to Genno")

    def on_return_to_validation(self):
        self.init_state()
        self.return_to_validation.emit()

    def export_csv(self):
        user_prefs = load_user_prefs()
        if "genno_export_folder" not in user_prefs:
            qw.QMessageBox.warning(
                self,
                "Export",
                "No export folder selected, please select one using the next dialog.",
            )
            genno_export_folder = qw.QFileDialog.getExistingDirectory(
                self, "Choose Genno export folder"
            )
            if genno_export_folder:
                save_user_prefs({"genno_export_folder": genno_export_folder})
            else:
                qw.QMessageBox.warning(
                    self,
                    "Export",
                    "No export folder selected, aborting export.",
                )
                return

    def on_next_step_clicked(self):
        # Export to genno
        if self.is_finished:
            self.export_csv()
            return

        # Increment the step index
        self.current_step_id += 1

        # Decide whether we continue or if we reached the end
        if self.current_step_id >= len(self.method):
            self.on_finish()
        else:
            self.setup_step()

    def set_method_path(self, method_path: Path):
        with open(method_path, "r") as f:
            self.method = json.load(f)

    def setup_step(self):
        """Modifies the query to match the current step definition."""
        if (
            not self.validation_name
            or not self.validation_parquet_files
            or not self.method
            or not self.datalake
            or self.current_step_id >= len(self.method)
            or self.current_step_id < 0
        ):
            return

        step_definition: List[dict] = self.method[self.current_step_id]

        self.title_label.setText(step_definition["title"])
        self.description_text.text_edit.setText(step_definition["description"])

        self.datalake.set_main_files(self.validation_parquet_files)

        self.datalake.mute()

        self.datalake.unmute()
        self.datalake.update_data()

        if not self.datalake.is_valid():
            print(self.datalake.to_do())

    def start_validation(self, selected_validation: dict):
        if not self.datalake or not self.datalake.conn:
            return

        self.validation_name = selected_validation["validation_name"]
        self.validation_parquet_files = selected_validation["parquet_files"]

        config_folder = get_config_folder()
        if not config_folder:
            qw.QMessageBox.critical(
                self,
                "Erreur",
                "Pas de dossier de configuration sélectionné, abandon.",
            )
            return

        self.validation_table_uuid = selected_validation["table_uuid"]
        self.set_method_path(
            Path(config_folder)
            / "validation_methods"
            / (selected_validation["validation_method"] + ".json")
        )
        try:
            self.current_step_id = (
                self.datalake.conn.sql(
                    f"SELECT last_step FROM validations WHERE table_uuid = '{self.validation_table_uuid}'"
                )
                .pl()
                .to_dicts()[0]["last_step"]
            )
            if self.current_step_id >= len(self.method):
                self.on_finish()
            else:
                self.setup_step()
        except IndexError:
            self.current_step_id = 0

    def save_state(self):
        if self.validation_table_uuid:
            save_user_prefs(
                {
                    "last_validation_table_uuid": self.validation_table_uuid,
                }
            )

    def load_state(self):
        userprefs = load_user_prefs()
        if "last_validation_table_uuid" in userprefs:
            self.validation_table_uuid = userprefs["last_validation_table_uuid"]
            if self.validation_table_uuid is not None and self.datalake.conn:
                self.start_validation(
                    get_validation_from_table_uuid(
                        self.datalake.conn, self.validation_table_uuid
                    )
                )
            else:
                # TODO: handle this case (should not happen)
                pass


class ValidationWidgetContainer(qw.QWidget):

    def __init__(self, datalake: DataLake, parent=None):
        super().__init__(parent)
        self.datalake = datalake

        self.validation_query = self.datalake.get_query("validation")

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

        self.setLayout(self._layout)

    def on_validation_start(self):
        if not self.validation_welcome_widget.get_selected_validation():
            qw.QMessageBox.warning(
                self,
                "Validation",
                "Veuillez sélectionner une validation à exécuter.",
            )
            return
        self.multi_widget.set_current_widget("validation")
        self.validation_widget.init_state()

        config_folder = get_config_folder()
        if not config_folder:
            qw.QMessageBox.critical(
                self,
                "Erreur",
                "Pas de dossier de configuration sélectionné, abandon.",
            )
            return

        selected_validation = self.validation_welcome_widget.get_selected_validation()

        self.validation_widget.start_validation(selected_validation)

    def on_return_to_validation(self):
        self.multi_widget.set_current_widget("welcome")
        self.validation_widget.init_state()
        self.validation_welcome_widget.model.update()

    def load_previous_session(self):
        userprefs = load_user_prefs()
        if "last_widget_shown" in userprefs:
            self.multi_widget.set_current_widget(userprefs["last_widget_shown"])

    def on_close(self):
        save_user_prefs(
            {"last_widget_shown": self.multi_widget.get_current_widget_name()}
        )


class IntroPage(qw.QWizardPage):

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.setTitle("Introduction")
        self.setSubTitle("Ce wizard vous permet de créer une nouvelle validation.")

        # Add a label with a lineedit to get the validation name
        self.validation_name_label = qw.QLabel("Nom de la validation:")
        self.validation_name_lineedit = qw.QLineEdit()
        self.validation_name_lineedit.setPlaceholderText("Nom de la validation")
        self.validation_name_lineedit.textChanged.connect(
            self.on_validation_name_changed
        )
        self.validation_name_lineedit.setValidator(
            qg.QRegularExpressionValidator(qc.QRegularExpression(r"^(\p{L}| |[0-9])+$"))
        )

        self.validation_method_combo = qw.QComboBox()
        userprefs = load_user_prefs()
        validation_methods = []
        if "config_folder" in userprefs:
            config_folder = Path(userprefs["config_folder"])
            validation_methods = [
                f.stem
                for f in config_folder.glob("validation_methods/*.json")
                if f.is_file()
            ]
        self.validation_method_combo.addItems(validation_methods)
        self.validation_method_combo.currentTextChanged.connect(
            self.on_validation_method_changed
        )

        layout = qw.QVBoxLayout()
        layout.addWidget(self.validation_name_label)
        layout.addWidget(self.validation_name_lineedit)
        layout.addWidget(self.validation_method_combo)
        self.setLayout(layout)

        self.data = data

        self.validation_method_combo.setCurrentIndex(-1)

    def initializePage(self):
        self.validation_name_lineedit.clear()
        self.data["validation_name"] = ""
        self.data["validation_method"] = ""

    def isComplete(self):
        return bool(self.data["validation_name"]) and bool(
            self.data["validation_method"]
        )

    def validatePage(self):
        return self.isComplete()

    def cleanupPage(self):
        self.validation_name_lineedit.clear()
        self.data["validation_name"] = ""
        self.data["validation_method"] = ""

    def on_validation_name_changed(self, text: str):
        was_valid = self.isComplete()
        self.data["validation_name"] = text

        if was_valid != self.isComplete():
            self.completeChanged.emit()

    def on_validation_method_changed(self, text: str):
        was_valid = self.isComplete()
        self.data["validation_method"] = text

        if was_valid != self.isComplete():
            self.completeChanged.emit()


class ParquetSelectPage(qw.QWizardPage):

    def __init__(self, datalake: DataLake, data: dict, parent=None):
        super().__init__(parent)
        self.setTitle("Run Selection")
        self.setSubTitle("Choisissez le(s) fichier(s) des runs à valider.")

        self.select_parquet_button = qw.QPushButton("Choisir le(s) run(s)...")
        self.select_parquet_button.clicked.connect(self.on_select_parquet_clicked)

        self.selected_files_label = qw.QLabel("")

        layout = qw.QVBoxLayout()
        layout.addWidget(self.select_parquet_button)
        layout.addWidget(self.selected_files_label)
        self.setLayout(layout)

        self.data = data
        self.datalake = datalake

    def on_select_parquet_clicked(self):

        valid_parquet_files_model = qg.QStandardItemModel()
        for f in Path(self.datalake.datalake_path).glob("genotypes/runs/*.parquet"):
            item = qg.QStandardItem(f.resolve().stem)
            item.setData(f.resolve().as_posix(), qc.Qt.ItemDataRole.UserRole)
            item.setEditable(False)
            item.setCheckable(True)
            valid_parquet_files_model.appendRow(item)
        table = SearchableTable(valid_parquet_files_model)
        table.view.setSelectionMode(qw.QAbstractItemView.SelectionMode.MultiSelection)
        table.view.verticalHeader().hide()
        table.view.horizontalHeader().hide()
        dlg = AnyWidgetDialog(table, "Please select one or more run to validate", self)
        if dlg.exec_() == qw.QDialog.DialogCode.Accepted:
            filenames = [
                (
                    valid_parquet_files_model.data(
                        valid_parquet_files_model.index(i, 0),
                        qc.Qt.ItemDataRole.UserRole,
                    ),
                    valid_parquet_files_model.data(
                        valid_parquet_files_model.index(i, 0),
                        qc.Qt.ItemDataRole.DisplayRole,
                    ),
                )
                for i in range(valid_parquet_files_model.rowCount())
                if valid_parquet_files_model.item(i).checkState()
                == qc.Qt.CheckState.Checked
            ]
            is_complete_before = self.isComplete()
            if filenames:
                self.data["file_names"] = filenames
                self.selected_files_label.setText(
                    "Fichiers sélectionnés:\n" + "\n".join(filenames)
                )

            if is_complete_before != self.isComplete():
                self.completeChanged.emit()

    def initializePage(self):
        self.data["file_names"] = []
        self.selected_files_label.setText("")

    def isComplete(self):
        return bool(self.data["file_names"])

    def validatePage(self):
        return bool(self.data["file_names"])

    def cleanupPage(self):
        self.data["file_names"] = []
        self.selected_files_label.setText("")


class SamplesSelectPage(qw.QWizardPage):

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.setTitle("Samples Selection")
        self.setSubTitle("Choisissez le(s) échantillon(s) à valider.")

        self.select_samples_button = qw.QPushButton("Select Samples")
        self.select_samples_button.clicked.connect(self.on_select_samples_clicked)

        self.selected_samples_label = qw.QLabel("")

        layout = qw.QVBoxLayout()
        layout.addWidget(self.select_samples_button)
        layout.addWidget(self.selected_samples_label)
        self.setLayout(layout)

        self.data = data

    def on_select_samples_clicked(self):
        is_complete_before = self.isComplete()
        samples_names = [
            d["sample_name"]
            for d in db.sql(
                f"SELECT DISTINCT sample_name FROM read_parquet({duck_db_literal_string_list(self.data['file_names'])})"
            )
            .pl()
            .to_dicts()
        ]
        sample_selector = StringListChooser(samples_names, self)
        if sample_selector.exec() == qw.QDialog.DialogCode.Accepted:
            self.data["sample_names"] = sample_selector.get_selected()
            self.selected_samples_label.setText(
                "Echantillons sélectionnés:\n" + "\n".join(self.data["sample_names"])
            )

        if is_complete_before != self.isComplete():
            self.completeChanged.emit()

    def initializePage(self):
        self.data["sample_names"] = []
        self.selected_samples_label.setText("")

    def isComplete(self):
        return bool(self.data["sample_names"])

    def cleanupPage(self):
        self.data["sample_names"] = []


class ValidationWizard(qw.QWizard):

    def __init__(self, datalake: DataLake, parent=None):
        super().__init__(parent)

        self.data = {
            "file_names": [],
            "sample_names": [],
            "validation_name": "",
            "validation_method": "",
        }

        self.datalake = datalake

        self.addPage(self.createIntroPage())
        self.addPage(self.createParquetSelectPage())
        self.addPage(self.createSamplesSelectPage())

        self.setOption(qw.QWizard.WizardOption.IndependentPages, False)

    def createIntroPage(self):
        page = IntroPage(self.data, self)
        return page

    def createParquetSelectPage(self):
        page = ParquetSelectPage(self.datalake, self.data, self)
        return page

    def createSamplesSelectPage(self):
        page = SamplesSelectPage(self.data, self)
        return page
