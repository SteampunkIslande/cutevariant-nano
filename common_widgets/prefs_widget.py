# A simple dialog that displays a QTabWidget to edit preferences.
# Preferences are stored in a JSON file, and initialized using a dictionary, which is passed to the constructor.
# The widget accepts two levels of nesting.
# Top level keys (i.e. those with no children) are in the 'General' tab.
# Keys with children are displayed in their own tab (the key is the tab name).
# Numbers are displayed as spinboxes, strings as line edits, and booleans as checkboxes.
# Colons can be used in the keys to specify the editor type (e.g. 'my_key:file' will add a get_open_file_name).

from typing import Union

import PySide6.QtWidgets as qw


class ExistingFileEditor(qw.QWidget):
    def __init__(self, filename: str, parent=None):
        super().__init__(parent)

        self._layout = qw.QHBoxLayout()

        self.editor = qw.QLineEdit()
        self.editor.setText(filename)
        self._layout.addWidget(self.editor)

        self.button = qw.QPushButton("...")
        self._layout.addWidget(self.button)

        self.button.clicked.connect(self.get_file_name)
        self.setLayout(self._layout)

    def get_file_name(self):
        file_name, _ = qw.QFileDialog.getOpenFileName(self)
        if file_name:
            self.editor.setText(file_name)

    def text(self):
        return self.editor.text()

    def setText(self, text):
        self.editor.setText(text)


class ExistingDirEditor(qw.QWidget):
    def __init__(self, filename: str, parent=None):
        super().__init__(parent)

        self._layout = qw.QHBoxLayout()

        self.editor = qw.QLineEdit()
        self.editor.setText(filename)
        self._layout.addWidget(self.editor)

        self.button = qw.QPushButton("...")
        self._layout.addWidget(self.button)

        self.button.clicked.connect(self.get_file_name)
        self.setLayout(self._layout)

    def get_file_name(self):
        file_name = qw.QFileDialog.getExistingDirectory(self)
        if file_name:
            self.editor.setText(file_name)

    def text(self):
        return self.editor.text()

    def setText(self, text):
        self.editor.setText(text)


class PrefsWidget(qw.QDialog):
    def __init__(self, prefs: dict, parent=None):
        super().__init__(parent)

        PrefsWidget.validate_prefs(prefs)

        self.prefs = {}
        for key, value in prefs.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    self.prefs[f"{key}.{sub_key}"] = sub_value
            else:
                self.prefs[f"General.{key}"] = value

        self.tab_widget = qw.QTabWidget()

        self.general_tab = qw.QWidget()
        self.general_layout = qw.QFormLayout()
        self.general_tab.setLayout(self.general_layout)
        self.tab_widget.addTab(self.general_tab, "General")

        self.tabs = {"General": self.general_tab}
        self.layouts = {"General": self.general_layout}
        self.editors = {}

        possible_values = None

        for key, value in self.prefs.items():
            main_key, sub_key = key.split(".", 1)

            if main_key in self.tabs:
                tab = self.tabs[main_key]
                layout = self.layouts[main_key]

            else:
                tab = qw.QWidget()
                layout = qw.QFormLayout()
                tab.setLayout(layout)
                self.tab_widget.addTab(tab, main_key)
                self.tabs[main_key] = tab
                self.layouts[main_key] = layout

            if ":" in sub_key:
                key_name, editor_type, *possible_values = sub_key.split(":")
            else:
                if type(value) == int:
                    editor_type = "integer"
                elif type(value) == bool:
                    editor_type = "bool"
                elif type(value) == float:
                    editor_type = "float"
                else:
                    editor_type = "string"
                key_name = sub_key

            self.add_editor(layout, key_name, editor_type, key, value, possible_values)

        self.save_button = qw.QPushButton("Save")
        self.save_button.setDefault(True)
        self.cancel_button = qw.QPushButton("Cancel")

        self.save_cancel_layout = qw.QHBoxLayout()
        self.save_cancel_layout.addStretch()
        self.save_cancel_layout.addWidget(self.save_button)
        self.save_cancel_layout.addWidget(self.cancel_button)

        self.save_button.clicked.connect(self.save_prefs)
        self.cancel_button.clicked.connect(self.reject)

        layout = qw.QVBoxLayout()
        layout.addWidget(self.tab_widget)

        layout.addLayout(self.save_cancel_layout)

        self.setLayout(layout)

    def add_editor(
        self,
        layout: qw.QFormLayout,
        key_name: str,
        editor_type: str,
        key: str,
        value: Union[str, int, bool],
        possible_values: list[str] = None,
    ):

        if editor_type == "existing_file":
            editor = ExistingFileEditor(value)
            layout.addRow(key_name, editor)
        elif editor_type == "existing_dir":
            editor = ExistingDirEditor(value)
            layout.addRow(key_name, editor)
        elif editor_type == "integer":
            editor = qw.QSpinBox()
            editor.setValue(value)
            layout.addRow(key_name, editor)
        elif editor_type == "float":
            editor = qw.QDoubleSpinBox()
            editor.setValue(value)
            layout.addRow(key_name, editor)
        elif editor_type == "bool":
            editor = qw.QCheckBox()
            editor.setChecked(value)
            layout.addRow(key_name, editor)
        elif editor_type == "combo_box":
            editor = qw.QComboBox()
            editor.addItems(possible_values)
            editor.setCurrentText(value)
            layout.addRow(key_name, editor)
        else:
            editor = qw.QLineEdit()
            editor.setText(str(value))
            layout.addRow(key_name, editor)
        self.editors[key] = editor

    def save_prefs(self):
        for key, editor in self.editors.items():
            if isinstance(editor, qw.QSpinBox):
                self.prefs[key] = editor.value()
            elif isinstance(editor, qw.QDoubleSpinBox):
                self.prefs[key] = editor.value()
            elif isinstance(editor, qw.QCheckBox):
                self.prefs[key] = editor.isChecked()
            elif isinstance(editor, ExistingFileEditor):
                self.prefs[key] = editor.text()
            elif isinstance(editor, qw.QLineEdit):
                self.prefs[key] = editor.text()
            elif isinstance(editor, ExistingDirEditor):
                self.prefs[key] = editor.text()
            elif isinstance(editor, qw.QComboBox):
                self.prefs[key] = editor.currentText()
            else:
                raise ValueError(f"Unknown editor type: {type(editor)}")
        new_prefs = {}
        for k, v in self.prefs.items():
            if "." in k:
                category_key, sub_key = k.split(".", 1)
                if category_key == "General":
                    new_prefs[sub_key] = v
                    continue
                if category_key not in new_prefs:
                    new_prefs[category_key] = {}
                new_prefs[category_key][sub_key] = v
            else:
                new_prefs[k] = v
        self.prefs = new_prefs
        self.accept()

    @staticmethod
    def validate_prefs(prefs: dict):
        for k, v in prefs.items():
            if isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    if not isinstance(sub_k, str):
                        raise ValueError(f"Key {sub_k} is not a string")
                    if isinstance(sub_v, dict):
                        raise ValueError(
                            "Nested dictionaries are not allowed. Max depth is 2"
                        )
                    if (
                        not isinstance(sub_v, (str, int, float, bool, list, tuple))
                        and sub_v is not None
                    ):
                        raise ValueError(
                            f"Value {sub_v} is not a JSON serializable type"
                        )


if __name__ == "__main__":
    import sys

    app = qw.QApplication(sys.argv)
    prefs = {
        "my_string:combo_box:RED:GREEN:BLUE": "BLUE",
        "my_number": 42,
        "my_bool": True,
        "my_file:existing_file": "/path/to/file",
        "other_weird_field:existing_dir": "weird",
        "Advanced": {
            "my_other_string": "world",
            "my_other_number": 24,
            "my_other_bool": False,
        },
    }
    widget = PrefsWidget(prefs)
    widget.exec()
    print(widget.prefs)
