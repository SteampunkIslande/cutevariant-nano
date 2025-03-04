import os
from typing import Union

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import app as ap
import datalake.datalake_component as dl
import query_manager.query_manager_component as qm
from common_widgets.multiwidget_holder import MultiWidgetHolder
from commons import yaml_load
from validation_manager.validation_model import ValidationModel
from validation_manager.validation_selection_widget import ValidationSelectionWidget
from validation_manager.validation_widget import ValidationWidget


class ValidationManagerComponent(ap.AppComponent):

    def __init__(
        self, app: ap.App, instance_name: str, parent_component: ap.AppComponent
    ):
        super().__init__(app, instance_name, parent_component)
        self.app = app
        self.instance_name = instance_name
        self.parent_component = parent_component

        self.datalake: dl.Datalake = app.get_component("datalake")

        # Query Manager Component
        self.query_manager_component: qm.QueryManagerComponent = (
            self.app.instantiate_singleton("query_manager")
        )

        self.datalake.folder_changed.connect(self.on_datalake_changed)

        self.widget_holder = MultiWidgetHolder()
        self.validation_model = ValidationModel(self.app, self.datalake, self)

        self.validation_selection_widget = ValidationSelectionWidget(
            self.app, self.datalake, self.validation_model
        )
        self.validation_widget = ValidationWidget(self.app, self.datalake)

        self.widget_holder.add_widget(
            self.validation_selection_widget, "validation_selection"
        )
        self.widget_holder.add_widget(self.validation_widget, "validation")

        self.widget_holder.set_current_widget("validation_selection")

        self.widget_holder.setWindowTitle(self.app.translate("Validation selection"))

        # Connect transition from validation selection to validation
        self.validation_selection_widget.validation_start.connect(
            self.on_validation_start
        )

        # Connect transition from validation back to selection validation
        self.validation_widget.return_to_validation.connect(
            self.on_back_to_validation_selection
        )

    def on_validation_start(self):
        validation_info = self.validation_selection_widget.get_selected_validation()
        self.widget_holder.set_current_widget("validation")

        self.set_validation(validation_info)

    def set_validation(self, validation_info: dict):

        # Completely new validation, forget all the queries we may have
        self.query_manager_component.clear()

        sample_names = validation_info.get("sample_names")
        if not sample_names:
            return
        validation_method = validation_info.get("validation_method")
        if not validation_method:
            return
        config_folder_present, config_folder = self.app.get_config_folder()
        if not config_folder_present:
            return

        self.validation_table_uuid = validation_info.get("table_uuid")
        self.validations_method = validation_info.get("validation_method")

        self.validations_method = yaml_load(
            os.path.join(
                config_folder, "validation_methods", validation_method + ".yaml"
            )
        )

        for sample_name in sample_names:
            self.query_manager_component.new_query(sample_name)

    def on_back_to_validation_selection(self):
        self.widget_holder.set_current_widget("validation_selection")

        # Close all queries from the validation we're leaving
        self.query_manager_component.clear()

    def validate(self):
        # self.validation_model
        pass

    def get_instance_name(self) -> str:
        return self.instance_name

    def load_from_session(self, session: dict):
        # Implement loading logic here
        pass

    def save_to_session(self) -> dict:
        # Implement saving logic here
        return {}

    def on_start(self):
        # Implement startup logic here
        pass

    def widget(self) -> Union[None, qw.QWidget]:
        return self.widget_holder

    def get_signal(self, signal_name: str) -> Union[qc.SignalInstance, None]:
        return None

    def get_menubar_entries(self) -> list[tuple[str, qg.QAction]]:
        # Implement menu bar entries here
        return []

    def get_contextmenu_entries(self, local_info: dict) -> list[tuple[str, qg.QAction]]:
        # Implement context menu entries here
        return []

    def on_datalake_changed(self):
        return


def register_component():
    return "validation_manager", {
        "instantiation_policy": "singleton",
        "instantiate_on": "demand",
        "class": ValidationManagerComponent,
    }
