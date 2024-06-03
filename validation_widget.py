import json
from pathlib import Path

import duckdb as db
import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

from common_widgets.multiwidget_holder import MultiWidgetHolder
from common_widgets.searchable_table import SearchableTable
from common_widgets.string_list_chooser import StringListChooser
from commons import duck_db_literal_string_list, load_user_prefs, save_user_prefs
from query import Field, Join, Query, Table
from validation_model import VALIDATION_TABLE_COLUMNS, ValidationModel


class ValidationWelcomeWidget(qw.QWidget):

    validation_start = qc.Signal()

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)
        self.query = query
        self.model = ValidationModel(self.query, self)

        self.query.query_changed.connect(self.on_query_changed)

        self._layout = qw.QVBoxLayout(self)

        self.new_validation_button = qw.QPushButton("New Validation", self)
        self.new_validation_button.clicked.connect(self.on_new_validation_clicked)

        self.start_validation_button = qw.QPushButton("Start Validation", self)
        self.start_validation_button.clicked.connect(self.on_start_validation_clicked)

        if not self.query:
            self.new_validation_button.setEnabled(False)
            self.start_validation_button.setEnabled(False)
        if not self.query.datalake_path:
            self.new_validation_button.setEnabled(False)
            self.start_validation_button.setEnabled(False)

        self.table = SearchableTable(self.model, parent=self)
        self.hide_unwanted_columns()

        self.init_layout()

    def hide_unwanted_columns(self):
        self.table.view.hideColumn(VALIDATION_TABLE_COLUMNS["table_uuid"])

    def on_new_validation_clicked(self):
        if not self.query:
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

        wizard = ValidationWizard(self, self)
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

    def on_query_changed(self):
        self.model.update()
        self.hide_unwanted_columns()
        if self.query and self.query.datalake_path:
            self.new_validation_button.setEnabled(True)
            self.start_validation_button.setEnabled(True)

    def get_selected_validation(self):
        selected = self.table.view.selectionModel().selectedRows()
        if selected:
            return selected[0].data(qc.Qt.ItemDataRole.UserRole)
        return None


class ValidationStep:

    def __init__(self, query: Query, step_definition: dict):
        self.step_definition = step_definition
        self.title = step_definition["title"]
        self.description = step_definition["description"]

        self.query = query

        self.tables = {}
        self.joins = []
        self.fields = []

        self.tables["main_table"] = self.query.main_table

        for table_def in step_definition["tables"]:
            self.tables[table_def["alias"]] = Table(
                table_def["name"], table_def["alias"]
            )
            self.joins.append(
                Join(
                    self.tables[table_def["alias"]],
                    left_on=Field(
                        table_def["join"]["left_on"],
                        self.tables[table_def["join"]["left_table"]],
                    ),
                    right_on=Field(
                        table_def["join"]["right_on"], self.tables[table_def["alias"]]
                    ),
                )
            )
        for field in step_definition["fields"]:
            self.fields.append(
                Field(
                    field["name"],
                    self.tables[field["table"]],
                    is_expression=field["is_expression"],
                ),
            )


class ValidationWidget(qw.QWidget):

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)
        self.query = query

        self.current_step_id = 0
        self.current_step = None
        self.method_path = None
        self.validation_table_uuid = None

        self._layout = qw.QVBoxLayout(self)

    def set_method_path(self, method_path: Path):
        self.method_path = method_path
        with open(method_path, "r") as f:
            self.method = json.load(f)

    def setup_step(self):
        try:
            step_definition = list(
                filter(lambda x: x["step_id"] == self.current_step_id, self.method)
            )[0]
            self.current_step = ValidationStep(self.query, step_definition)
            self.query.mute()

            # CLEAR JOINS
            self.query.clear_additional_tables()
            # ADD JOINS
            for join in self.current_step.joins:
                self.query.add_join(join)

            # CLEAR FIELDS
            self.query.clear_fields()
            # ADD FIELDS
            for field in self.current_step.fields:
                self.query.add_field(field)

            self.query.unmute()
            self.query.update()
            if not self.query.is_valid():
                print(self.query.to_do())
        except IndexError:
            print("Step not found")
            return

    def start_validation(self, selected_validation: dict):
        try:
            config_folder = Path(load_user_prefs()["config_folder"])
        except KeyError:
            qw.QMessageBox.warning(
                self,
                "Validation",
                "Pas de dossier de configuration trouvé, veuillez en choisir un.",
            )
            config_folder = qw.QFileDialog.getExistingDirectory(
                self, "Pas de dossier de configuration trouvé, veuillez en choisir un."
            )
            if config_folder:
                save_user_prefs({"config_folder": config_folder})
            else:
                return

        validation_table_uuid = selected_validation["table_uuid"]
        method_path = (
            Path(config_folder)
            / "validation_methods"
            / (selected_validation["validation_method"] + ".json")
        )
        if not self.query or not self.query.conn:
            return
        self.validation_table_uuid = validation_table_uuid
        self.set_method_path(method_path)
        try:
            self.current_step_id = (
                self.query.conn.sql(
                    f"SELECT last_step FROM validations WHERE table_uuid = '{validation_table_uuid}'"
                )
                .pl()
                .to_dicts()[0]["last_step"]
            )
            self.query.set_main_files(selected_validation["parquet_files"])
            self.query.set_table_validation_name(selected_validation["validation_name"])
            self.setup_step()
        except IndexError:
            self.current_step_id = 0


class ValidationWidgetContainer(qw.QWidget):

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)
        self.query = query

        self._layout = qw.QVBoxLayout(self)

        self.validation_welcome_widget = ValidationWelcomeWidget(self.query, self)
        self.validation_welcome_widget.validation_start.connect(
            self.on_validation_start
        )

        self.validation_widget = ValidationWidget(self.query, self)

        self.multi_widget = MultiWidgetHolder(self)
        self.multi_widget.add_widget(self.validation_welcome_widget, "welcome")
        self.multi_widget.add_widget(self.validation_widget, "validation")

        self.multi_widget.set_current_widget("welcome")

        self._layout.addWidget(self.multi_widget)

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
        try:
            config_folder = Path(load_user_prefs()["config_folder"])
        except KeyError:
            qw.QMessageBox.warning(
                self,
                "Validation",
                "Pas de dossier de configuration trouvé, veuillez en choisir un.",
            )
            config_folder = qw.QFileDialog.getExistingDirectory(
                self, "Pas de dossier de configuration trouvé, veuillez en choisir un."
            )
            if config_folder:
                save_user_prefs({"config_folder": config_folder})
            else:
                return

        selected_validation = self.validation_welcome_widget.get_selected_validation()

        self.validation_widget.start_validation(selected_validation)


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

    def __init__(self, data: dict, parent=None):
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

    def on_select_parquet_clicked(self):
        filenames, _ = qw.QFileDialog.getOpenFileNames(
            self, "Open Parquet File", "", "Parquet Files (*.parquet)"
        )
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

    def __init__(self, validation_widget: ValidationWelcomeWidget, parent=None):
        super().__init__(parent)
        self.validation_widget = validation_widget

        self.data = {
            "file_names": [],
            "sample_names": [],
            "validation_name": "",
            "validation_method": "",
        }

        self.addPage(self.createIntroPage())
        self.addPage(self.createParquetSelectPage())
        self.addPage(self.createSamplesSelectPage())

        self.setOption(qw.QWizard.WizardOption.IndependentPages, False)

    def createIntroPage(self):
        page = IntroPage(self.data)
        return page

    def createParquetSelectPage(self):
        page = ParquetSelectPage(self.data)
        return page

    def createSamplesSelectPage(self):
        page = SamplesSelectPage(self.data)
        return page
