import json

import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

import app as ap
import fields.fields_component as fld_cmp
import fields.fields_model as fldm
from common_widgets.searchable_list import SearchableList


class PresetsWidget(qw.QWidget):

    preset_changed = qc.Signal()

    def __init__(self, app: ap.App, model: fldm.FieldsModel):
        super().__init__()

        self.app = app
        self.model = model

        self.add_to_presets_button = qw.QPushButton(
            self.app.translate("Add to presets")
        )
        self.presets_combobox = qw.QComboBox()
        self.add_to_presets_button.clicked.connect(self.add_to_presets)

        self.presets = {}

        layout = qw.QVBoxLayout(self)

        layout.addWidget(self.add_to_presets_button)
        layout.addWidget(self.presets_combobox)

        self.presets_combobox.currentIndexChanged.connect(self.preset_changed)

        self.load_presets()

        self.setLayout(layout)

    def get_selected_fields(self):
        return self.presets_combobox.currentData(qc.Qt.ItemDataRole.UserRole)["fields"]

    def load_presets(self):
        success, config_folder = self.app.get_config_folder()
        if not success:
            return
        presets_file = config_folder / "presets" / "presets.json"
        if not presets_file.exists():
            return
        with open(presets_file) as f:
            self.presets = json.load(f)
        if "fields" not in self.presets:
            return

        self.presets_combobox.clear()
        for preset_name, preset_data in self.presets["fields"].items():
            self.presets_combobox.addItem(preset_name, preset_data)
        if self.presets_combobox.count() >= 1:
            self.presets_combobox.setCurrentIndex(0)

    def add_to_presets(self):
        # Caution: NOT THREAD SAFE!
        # This writes presets to disk in a synchronous way and without any locking.
        preset_name, ok = qw.QInputDialog.getText(
            self,
            self.app.translate("Add to presets"),
            self.app.translate("Enter preset name"),
        )
        if not ok:
            return
        if "fields_presets" not in self.presets:
            self.presets["fields_presets"] = {}
        self.presets["fields_presets"][preset_name] = {
            "fields": self.model.checked_fields(),
        }
        success, config_folder = self.app.get_config_folder()
        if not success:
            return
        presets_file = config_folder / "presets" / "presets.json"
        # Create if not exists
        presets_file.parent.mkdir(parents=True, exist_ok=True)
        with open(presets_file, "w") as f:
            json.dump(self.presets, f, ensure_ascii=False)
        self.presets_combobox.blockSignals(True)
        self.load_presets()
        self.presets_combobox.blockSignals(False)

    def __del__(self):
        print("PresetsWidget deleted")


class FieldsWidget(qw.QWidget):
    def __init__(self, app: ap.App, component: "fld_cmp.FieldsComponent"):
        super().__init__()

        self.app = app
        self.component = component
        self.model = self.component.model

        self.proxy_model = qc.QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterRegularExpression("^[^.].+$")

        self.searchable_list = SearchableList(self.proxy_model)
        self.searchable_list.view.setDragDropMode(
            qw.QAbstractItemView.DragDropMode.InternalMove
        )

        self.presets_widget = PresetsWidget(self.app, self.model)
        self.presets_widget.preset_changed.connect(
            lambda: self.model.set_checked_fields(
                self.presets_widget.get_selected_fields()
            )
        )

        layout = qw.QHBoxLayout(self)
        layout.addWidget(self.searchable_list)
        layout.addWidget(self.presets_widget)
        self.setLayout(layout)

    def __del__(self):
        print("FieldsWidget deleted")
