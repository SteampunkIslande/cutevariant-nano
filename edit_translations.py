import os
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import subprocess

import json

import jinja2

# A simple widget that reads a translations.json file and displays the translations in a table.


def extract_translations(output_file: str):

    translations_statements = subprocess.run(
        [
            "ast-grep",
            "run",
            "--json",
            "-p",
            """$CALLER.translate("$LITERAL")""",
        ],
        capture_output=True,
        text=True,
    )
    statements = json.loads(translations_statements.stdout)

    texts_to_be_translated = sorted(
        {item["metaVariables"]["single"]["LITERAL"]["text"] for item in statements}
    )

    try:
        from translations import TRANSLATIONS
    except ImportError:
        TRANSLATIONS = {}

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


class TranslationWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Translation editor")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self._layout = QVBoxLayout()
        self.central_widget.setLayout(self._layout)

        # Add menu: File -> Open translations file
        self.file_menu = self.menuBar().addMenu("File")
        self.open_translations_action = QAction("Open translations file")
        self.open_translations_action.setShortcut("Ctrl+O")
        self.open_translations_action.triggered.connect(self.open_translations_file)

        # Add menu: File -> Extract translations
        self.extract_translations_action = QAction(
            "Extract translations from current directory"
        )
        self.extract_translations_action.triggered.connect(self.extract_translations)
        self.extract_translations_action.setShortcut("Ctrl+E")

        # Add menu: File -> Save translations file
        self.save_translations_action = QAction("Save raw translations file")
        self.save_translations_action.triggered.connect(self.save_raw_translations)
        self.save_translations_action.setShortcut("Ctrl+S")

        # Add menu: File -> Write python translations file
        self.write_python_translations_action = QAction(
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

        self.model = QStandardItemModel()
        self.model.dataChanged.connect(self.on_data_changed)

        self.setup_ui()

    def setup_ui(self):
        self.combo_box = QComboBox()
        self.combo_box.setModel(self.model)

        self.table_view = QTableView()
        self.table_view.setModel(self.model)

        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().hide()

        self.combo_box.currentIndexChanged.connect(self.on_language_changed)

        self._layout.addWidget(self.combo_box)
        self._layout.addWidget(self.table_view)

    def open_translations_file(self):

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open translations file", "", "JSON files (*.json)"
        )

        if not os.path.isfile(file_path):
            return

        with open(file_path, "r", encoding="utf-8") as f:
            self.translations: dict[str, dict[str, str]] = json.load(f)

        # A tree model, with each node representing a language and the children representing the translations.

        # Display using a QTableView, as well as a combobox to select the language.

        self.model.clear()
        self.model.blockSignals(True)
        for lang, translations in self.translations.items():
            parent = QStandardItem(lang)
            self.model.appendRow(parent)
            for key, value in translations.items():
                key_item = QStandardItem(key)
                value_item = QStandardItem(value)

                if not value:
                    bold_font = key_item.font()
                    bold_font.setBold(True)
                    key_item.setFont(bold_font)
                    key_item.setForeground(QColor("#FFCCCC"))
                else:
                    normal_font = key_item.font()
                    normal_font.setBold(False)
                    key_item.setFont(normal_font)
                    key_item.setForeground(QColor("#000000"))

                value_item.setEditable(True)
                parent.appendRow([key_item, value_item])
        self.model.blockSignals(False)

    def extract_translations(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save translations file", "", "JSON files (*.json)"
        )
        if file_path:
            extract_translations(file_path)

    def save_raw_translations(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save translations file", "", "JSON files (*.json)"
        )

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.translations, f, indent=4, ensure_ascii=False)

    def write_python_translations(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save translations file", "", "Python files (*.py)"
        )
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

    def on_data_changed(self, top_left: QModelIndex, bottom_right: QModelIndex):
        # Just save the data to the translations dictionary.
        lang = self.combo_box.currentText()
        key_item = self.model.itemFromIndex(top_left.siblingAtColumn(0))
        key = key_item.text()
        value_item = self.model.itemFromIndex(top_left.siblingAtColumn(1))
        value = value_item.text()

        if not value:
            bold_font = key_item.font()
            bold_font.setBold(True)
            key_item.setFont(bold_font)
            key_item.setForeground(QColor("#FFCCCC"))
        else:
            normal_font = key_item.font()
            normal_font.setBold(False)
            key_item.setFont(normal_font)
            key_item.setForeground(QColor("#000000"))

        self.translations[lang][key] = value


if __name__ == "__main__":
    app = QApplication([])
    window = TranslationWindow()
    window.show()
    app.exec()
