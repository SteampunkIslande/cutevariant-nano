#!/usr/bin/env python

import importlib
import json
import os
import subprocess

import jinja2
import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

# A simple widget that reads a translations.json file and displays the translations in a table.


def extract_translations(
    directory: str,
    output_file: str,
    pattern: str = """$CALLER.translate("$LITERAL")""",
    existing_translations_file: str = "translations.py",
):

    translations_statements = subprocess.run(
        ["ast-grep", "run", "--json", "-p", pattern, directory],
        capture_output=True,
        text=True,
    )
    statements = json.loads(translations_statements.stdout)

    texts_to_be_translated = sorted(
        {item["metaVariables"]["single"]["LITERAL"]["text"] for item in statements}
    )

    spec = importlib.util.spec_from_file_location(
        "translations", os.path.join(directory, existing_translations_file)
    )
    translation_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(translation_module)
    TRANSLATIONS: dict[str, dict[str, str]] = getattr(
        translation_module, "TRANSLATIONS"
    )

    all_translations = {}

    for lang, translation in TRANSLATIONS.items():
        all_translations[lang] = {
            text: translation.get(text, "") for text in texts_to_be_translated
        }

    with open(output_file, "w", encoding="utf-8") as f:

        json.dump(
            all_translations,
            f,
            indent=4,
            ensure_ascii=False,
        )


class TranslationWindow(qw.QMainWindow):

    def __init__(self, simple_mode: bool = False):
        super().__init__()

        self.setWindowTitle("Translation editor")

        self.central_widget = qw.QWidget()
        self.setCentralWidget(self.central_widget)

        self._layout = qw.QVBoxLayout()
        self.central_widget.setLayout(self._layout)

        # Add menu: File -> Open translations file
        self.file_menu = self.menuBar().addMenu("File")
        self.open_translations_action = qg.QAction("Open translations file")
        self.open_translations_action.setShortcut("Ctrl+O")
        self.open_translations_action.triggered.connect(self.open_translations_file)

        # Add menu: File -> Extract translations
        self.extract_translations_action = qg.QAction("Extract translations")
        self.extract_translations_action.triggered.connect(self.extract_translations)
        self.extract_translations_action.setShortcut("Ctrl+E")

        # Add menu: File -> Save translations file
        self.save_translations_action = qg.QAction("Save raw translations file")
        self.save_translations_action.triggered.connect(self.save_raw_translations)
        self.save_translations_action.setShortcut("Ctrl+S")

        # Add menu: File -> Write python translations file
        self.write_python_translations_action = qg.QAction(
            "Write python translations file"
        )
        self.write_python_translations_action.triggered.connect(
            self.write_python_translations
        )
        self.write_python_translations_action.setShortcut("Ctrl+B")

        self.file_menu.addAction(self.extract_translations_action)
        self.file_menu.addAction(self.open_translations_action)
        self.file_menu.addAction(self.save_translations_action)
        self.file_menu.addAction(self.write_python_translations_action)

        self.model = qg.QStandardItemModel(0, 2)
        self.model.setHorizontalHeaderLabels(["Program literal", "Translation"])
        self.model.dataChanged.connect(self.on_data_changed)

        self.simple_mode = simple_mode

        self.translation_file = None

        if self.simple_mode:
            self.translation_file = os.path.join(
                os.path.dirname(__file__), "translations.json"
            )

        self.setup_ui()

    def setup_ui(self):
        self.combo_box = qw.QComboBox()
        self.combo_box.setModel(self.model)

        self.table_view = qw.QTableView()
        self.table_view.setModel(self.model)

        self.table_view.horizontalHeader().setStretchLastSection(True)
        # self.table_view.horizontalHeader().hide()

        self.combo_box.currentIndexChanged.connect(self.on_language_changed)

        self._layout.addWidget(self.combo_box)
        self._layout.addWidget(self.table_view)

        # Hacky way to setup fonts and colors for the table view.
        item = qg.QStandardItem("")
        self.normal_font = item.font()
        self.default_background = item.background()
        self.redish_background = qg.QColor(255, 153, 153)

        self.bold_font = qg.QFont(self.normal_font)
        self.bold_font.setBold(True)

        self.table_view.verticalHeader().hide()

    def open_translations_file(self):

        if not self.simple_mode:

            file_path, _ = qw.QFileDialog.getOpenFileName(
                self, "Open translations file", "", "JSON files (*.json)"
            )

            if not os.path.isfile(file_path):
                return

            self.translation_file = file_path

        with open(self.translation_file, "r", encoding="utf-8") as f:
            self.translations: dict[str, dict[str, str]] = json.load(f)

        # A tree model, with each node representing a language and the children representing the translations.

        # Display using a QTableView, as well as a combobox to select the language.

        self.model.clear()
        self.model.blockSignals(True)
        self.model.setHorizontalHeaderLabels(["Program literal", "Translation"])
        for lang, translations in self.translations.items():
            parent = qg.QStandardItem(lang)
            self.model.appendRow(parent)
            for key, value in translations.items():
                key_item = qg.QStandardItem(key)
                value_item = qg.QStandardItem(value)

                if not value:
                    key_item.setFont(self.bold_font)
                    value_item.setBackground(self.redish_background)
                else:
                    key_item.setFont(self.normal_font)
                    value_item.setBackground(self.default_background)

                value_item.setEditable(True)
                parent.appendRow([key_item, value_item])
        self.model.blockSignals(False)

    def extract_translations(self):

        if self.simple_mode:
            source_code_dir = os.path.dirname(__file__)
            file_path = os.path.join(os.path.dirname(__file__), "translations.json")
        else:

            source_code_dir = qw.QFileDialog.getExistingDirectory(
                self, "Select source code directory"
            )
            if not source_code_dir:
                return

            file_path, _ = qw.QFileDialog.getSaveFileName(
                self, "Save translations file", "", "JSON files (*.json)"
            )
        if file_path:
            extract_translations(source_code_dir, file_path)

        if self.simple_mode:
            self.open_translations_file()

    def save_raw_translations(self):
        if self.simple_mode:
            file_path = os.path.join(os.path.dirname(__file__), "translations.json")
        else:
            file_path, _ = qw.QFileDialog.getSaveFileName(
                self,
                "Save translations file (can override existing translations)",
                dir=(
                    os.path.basename(self.translation_file)
                    if self.translation_file
                    else qc.QDir.homePath()
                ),
                filter="JSON files (*.json)",
            )

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.translations, f, indent=4, ensure_ascii=False)

    def write_python_translations(self):
        if not self.simple_mode:
            file_path, _ = qw.QFileDialog.getSaveFileName(
                self, "Save translations file", "", "Python files (*.py)"
            )
        else:
            file_path = os.path.join(os.path.dirname(__file__), "translations.py")

        # Using jinja, and the current translations dictionary, write a python file that can be imported to use the translations.
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                template = jinja2.FileSystemLoader(os.path.dirname(__file__))
                env = jinja2.Environment(loader=template)
                template = env.get_template("translations-template.py.jinja2")
                f.write(
                    template.render(
                        languages=list(self.translations.keys()),
                        translations=self.translations,
                    )
                )

    def on_language_changed(self, index: int):
        self.table_view.setRootIndex(self.model.index(index, 0))

    def on_data_changed(self, top_left: qc.QModelIndex, bottom_right: qc.QModelIndex):
        # Just save the data to the translations dictionary.
        lang = self.combo_box.currentText()
        key_item = self.model.itemFromIndex(top_left.siblingAtColumn(0))
        key = key_item.text()
        value_item = self.model.itemFromIndex(top_left.siblingAtColumn(1))
        value = value_item.text()

        if not value:
            key_item.setFont(self.bold_font)
            value_item.setBackground(self.redish_background)
        else:
            key_item.setFont(self.normal_font)
            value_item.setBackground(self.default_background)

        self.translations[lang][key] = value


if __name__ == "__main__":
    app = qw.QApplication([])
    import sys

    window = TranslationWindow(simple_mode=len(sys.argv) > 1)
    window.show()
    app.exec()
