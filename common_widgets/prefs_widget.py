# A simple dialog that displays a QTabWidget to edit preferences.
# Preferences are stored in a JSON file, and initialized using a dictionary, which is passed to the constructor.
# The widget accepts two levels of nesting.
# Top level keys (i.e. those with no children) are in the 'General' tab.
# Keys with children are displayed in their own tab (the key is the tab name).
# Numbers are displayed as spinboxes, strings as line edits, and booleans as checkboxes.
# Colons can be used in the keys to specify the editor type (e.g. 'my_key:file' will add a get_open_file_name).

from typing import Union

import PySide6.QtWidgets as qw


class PrefsWidget(qw.QDialog):
    def __init__(self, prefs: dict, parent=None):
        super().__init__(parent)

        self.prefs = prefs

        self.tab_widget = qw.QTabWidget()

        self.general_tab = qw.QWidget()
        self.general_layout = qw.QFormLayout()
        self.general_tab.setLayout(self.general_layout)
        self.tab_widget.addTab(self.general_tab, "General")

        self.tabs = {"General": self.general_layout}

        for key, value in prefs.items():
            if isinstance(value, dict):
                tab = qw.QWidget()
                layout = qw.QFormLayout()
                tab.setLayout(layout)
                self.tabs[key] = layout
                self.tab_widget.addTab(tab, key)

                for sub_key, sub_value in value.items():
                    self.add_editor(layout, sub_key, sub_value)
            else:
                self.add_editor(self.general_layout, key, value)

        self.save_button = qw.QPushButton("Save")
        self.save_button.clicked.connect(self.save_prefs)

        layout = qw.QVBoxLayout()
        layout.addWidget(self.tab_widget)
        layout.addWidget(self.save_button)
        self.setLayout(layout)

    def add_editor(
        self, layout: qw.QFormLayout, key: str, value: Union[str, int, bool]
    ):
        if ":" in key:
            key, editor_type = key.split(":")
        else:
            editor_type = "string"

        if editor_type == "file":
            editor = qw.QLineEdit()
            button = qw.QPushButton("...")
            button.clicked.connect(
                lambda: editor.setText(qw.QFileDialog.getOpenFileName(self)[0])
            )
            layout.addRow(key, editor)
            layout.addWidget(button)
        elif editor_type == "number":
            editor = qw.QSpinBox()
            editor.setValue(value)
            layout.addRow(key, editor)
        elif editor_type == "bool":
            editor = qw.QCheckBox()
            editor.setChecked(value)
            layout.addRow(key, editor)
        else:
            editor = qw.QLineEdit()
            editor.setText(value)
            layout.addRow(key, editor)

    def save_prefs(self):
        for tab_name, layout in self.tabs.items():
            for i in range(layout.rowCount()):
                label: qw.QLabel = layout.itemAt(
                    i, qw.QFormLayout.ItemRole.FieldRole
                ).widget()
                key = label.text()
                editor = layout.itemAt(i, qw.QFormLayout.ItemRole.FieldRole).widget()
                if isinstance(editor, qw.QLineEdit):
                    self.prefs[tab_name][key] = editor.text()
                elif isinstance(editor, qw.QSpinBox):
                    self.prefs[tab_name][key] = editor.value()
                elif isinstance(editor, qw.QCheckBox):
                    self.prefs[tab_name][key] = editor.isChecked()
