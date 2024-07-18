from pathlib import Path

import duckdb as db
import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

from common_widgets.any_widget_dialog import AnyWidgetDialog
from common_widgets.searchable_table import SearchableTable
from common_widgets.string_list_chooser import StringListChooser
from commons import duck_db_literal_string_list, load_user_prefs, yaml_load
from datalake import DataLake


class IntroPage(qw.QWizardPage):

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.setTitle(qc.QCoreApplication.tr("Introduction"))
        self.setSubTitle(
            qc.QCoreApplication.tr(
                "Ce wizard vous permet de créer une nouvelle validation."
            )
        )

        # Add a label with a lineedit to get the validation name
        self.validation_name_label = qw.QLabel(
            qc.QCoreApplication.tr("Nom de la validation:")
        )
        self.validation_name_lineedit = qw.QLineEdit()
        self.validation_name_lineedit.setPlaceholderText(
            qc.QCoreApplication.tr("Nom de la validation")
        )
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
                for f in config_folder.glob("validation_methods/*.yaml")
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
        self.setTitle(qc.QCoreApplication.tr("Sélection du run"))
        self.setSubTitle(
            qc.QCoreApplication.tr("Choisissez le(s) fichier(s) des runs à valider.")
        )

        self.select_parquet_button = qw.QPushButton(
            qc.QCoreApplication.tr("Choisir le(s) run(s)...")
        )
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
            item.setData(
                str(f.relative_to(self.datalake.datalake_path)),
                qc.Qt.ItemDataRole.UserRole,
            )
            item.setEditable(False)
            item.setCheckable(True)
            valid_parquet_files_model.appendRow(item)
        table = SearchableTable(valid_parquet_files_model)
        table.view.setSelectionMode(qw.QAbstractItemView.SelectionMode.SingleSelection)
        table.view.verticalHeader().hide()
        table.view.horizontalHeader().hide()
        dlg = AnyWidgetDialog(
            table,
            qc.QCoreApplication.tr(
                "Veuillez sélectionner un ou plusieurs runs à valider"
            ),
            self,
        )
        if dlg.exec_() == qw.QDialog.DialogCode.Accepted:
            filenames_full_path, filenames = zip(
                *[
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
            )
            is_complete_before = self.isComplete()
            if filenames:
                self.data["file_names"] = filenames_full_path
                self.selected_files_label.setText(
                    qc.QCoreApplication.tr("Fichiers sélectionnés:\n")
                    + "\n".join(filenames)
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

    def __init__(self, datalake: DataLake, data: dict, parent=None):
        super().__init__(parent)
        self.setTitle(qc.QCoreApplication.tr("Sélection des échantillons"))
        self.setSubTitle(
            qc.QCoreApplication.tr("Choisissez le(s) échantillon(s) à valider.")
        )

        self.select_samples_button = qw.QPushButton(
            qc.QCoreApplication.tr("Sélectionner les échantillons")
        )
        self.select_samples_button.clicked.connect(self.on_select_samples_clicked)

        self.selected_samples_label = qw.QLabel("")

        layout = qw.QVBoxLayout()
        layout.addWidget(self.select_samples_button)
        layout.addWidget(self.selected_samples_label)
        self.setLayout(layout)

        self.datalake = datalake
        self.data = data

    def on_select_samples_clicked(self):
        is_complete_before = self.isComplete()
        samples_names = [
            d["sample_name"]
            for d in db.sql(
                f"SELECT DISTINCT sample_name FROM read_parquet({duck_db_literal_string_list(self.datalake.relative_to_absolute(f) for f in self.data['file_names'])})"
            )
            .pl()
            .to_dicts()
        ]
        sample_selector = StringListChooser(samples_names, self)
        if sample_selector.exec() == qw.QDialog.DialogCode.Accepted:
            self.data["sample_names"] = sample_selector.get_selected()
            self.selected_samples_label.setText(
                qc.QCoreApplication.tr("Echantillons sélectionnés:\n")
                + "\n".join(self.data["sample_names"])
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


class GeneListSelectPage(qw.QWizardPage):
    def __init__(self, datalake: DataLake, data: dict, parent=None):
        super().__init__(parent)
        self.setTitle(qc.QCoreApplication.tr("Sélection de la liste de gènes"))
        self.setSubTitle(
            qc.QCoreApplication.tr("Choisissez la liste de gènes à valider.")
        )

        self.select_genes_button = qw.QPushButton(
            qc.QCoreApplication.tr("Sélectionner les gènes")
        )
        self.select_genes_button.clicked.connect(self.on_select_genes_clicked)

        self.selected_genes_label = qw.QLabel("")

        layout = qw.QVBoxLayout()
        layout.addWidget(self.select_genes_button)
        layout.addWidget(self.selected_genes_label)
        self.setLayout(layout)

        self.datalake = datalake
        self.data = data

    def on_select_genes_clicked(self):
        is_complete_before = self.isComplete()
        import json

        validation_method = dict()
        if "validation_method" in self.data:

            validation_method: dict[str, dict] = yaml_load(
                Path(load_user_prefs()["config_folder"])
                / Path("validation_methods")
                / Path(self.data["validation_method"] + ".yaml")
            )
            gene_sets = validation_method.get("genes_list", dict()).keys()
        else:
            gene_sets = []

        gene_selector = StringListChooser(gene_sets, self)
        if gene_selector.exec() == qw.QDialog.DialogCode.Accepted:
            selected_gene_sets = gene_selector.get_selected()
            self.data["gene_names"] = []
            for selected_gene_set in selected_gene_sets:
                self.data["gene_names"].extend(
                    validation_method["genes_list"][selected_gene_set]
                )
            CR = "\n"
            self.selected_genes_label.setText(
                qc.QCoreApplication.tr(
                    "Panel(s): {0}{CR}Gène(s) sélectionné(s):{CR}{1}".format(
                        ", ".join(selected_gene_sets),
                        CR.join(self.data["gene_names"]),
                        CR=CR,
                    )
                )
            )

        if is_complete_before != self.isComplete():
            self.completeChanged.emit()

    def initializePage(self):
        self.data["gene_names"] = []
        self.selected_genes_label.setText("")

    def isComplete(self):
        return bool(self.data["gene_names"])

    def cleanupPage(self):
        self.data["gene_names"] = []


class ValidationWizard(qw.QWizard):

    def __init__(self, datalake: DataLake, parent=None):
        super().__init__(parent)

        self.data = {
            "file_names": [],
            "sample_names": [],
            "gene_names": [],
            "validation_name": "",
            "validation_method": "",
        }

        self.datalake = datalake

        self.addPage(self.createIntroPage())
        self.addPage(self.createGeneListSelectPage())
        self.addPage(self.createParquetSelectPage())
        self.addPage(self.createSamplesSelectPage())

        self.setOption(qw.QWizard.WizardOption.IndependentPages, False)

    def createIntroPage(self):
        page = IntroPage(self.data, self)
        return page

    def createGeneListSelectPage(self):
        page = GeneListSelectPage(self.datalake, self.data, self)
        return page

    def createParquetSelectPage(self):
        page = ParquetSelectPage(self.datalake, self.data, self)
        return page

    def createSamplesSelectPage(self):
        page = SamplesSelectPage(self.datalake, self.data, self)
        return page
