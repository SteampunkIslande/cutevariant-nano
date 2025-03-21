import os
from pathlib import Path
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

        # Query Manager Component
        query_manager_component: qm.QueryManagerComponent = (
            self.app.instantiate_singleton("query_manager")
        )

        self.widget_holder = MultiWidgetHolder()
        self.validation_model = ValidationModel(self.app, self)

        self.validation_selection_widget = ValidationSelectionWidget(
            self.app, self.validation_model, self
        )
        self.validation_widget = ValidationWidget(self.app, self)

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
        self.validation_widget.export_to_genno.connect(self.export_to_genno)
        self.validation_widget.validate.connect(self.validate)

    def on_validation_start(self):
        validation_info = self.validation_selection_widget.get_selected_validation()
        self.widget_holder.set_current_widget("validation")

        self.set_validation(validation_info)

    def init_validation(self, validation_info: dict):
        self.sample_names = validation_info.get("sample_names")
        if not self.sample_names:
            return
        self.validation_method = validation_info.get("validation_method")
        if not self.validation_method:
            return
        config_folder_present, config_folder = self.app.get_config_folder()
        if not config_folder_present:
            return

        validation_method = validation_info.get("validation_method")

        self.validation_method = yaml_load(
            os.path.join(
                config_folder, "validation_methods", validation_method + ".yaml"
            )
        )

        self.table_uuid = validation_info.get("table_uuid")
        self.gene_names = validation_info.get("gene_names")
        self.parquet_files = validation_info.get("parquet_files")

    def set_validation(self, validation_info: dict):
        # Completely new validation, forget all the queries we may have
        query_manager_component: qm.QueryManagerComponent = self.app.get_component(
            "query_manager"
        )
        query_manager_component.clear()

        self.init_validation(validation_info)

        # Add final validation query
        query_manager_component.new_query(
            self.app.translate("Final validation"),
            self.validation_method["final"]["query"],
            {
                "sample_names": self.sample_names,
                "table_uuid": self.table_uuid,
                "gene_names": self.gene_names,
                "parquet_files": self.parquet_files,
            },
        )

        for sample_name in self.sample_names:
            query_manager_component.new_query(
                sample_name,
                self.validation_method["default"]["query"],
                {
                    "sample_names": [sample_name],
                    "table_uuid": self.table_uuid,
                    "gene_names": self.gene_names,
                    "parquet_files": self.parquet_files,
                },
            )

    def validate(self):
        query_manager_component: qm.QueryManagerComponent = self.app.get_component(
            "query_manager"
        )
        # Close all queries, replace with the final one
        query_manager_component.clear()
        query_manager_component.new_query(
            self.app.translate("Final validation"),
            self.validation_method["final"]["query"],
            {
                "sample_names": self.sample_names,
                "table_uuid": self.table_uuid,
                "gene_names": self.gene_names,
                "parquet_files": self.parquet_files,
            },
        )

    def export_to_genno(self):
        if not self.validation_method:
            return

        user_prefs = self.app.load_user_prefs()
        if "genno_export_folder" not in user_prefs:
            qw.QMessageBox.warning(
                self,
                self.app.translate("Export"),
                self.app.translate(
                    "No Genno export folder selected, please choose one."
                ),
            )
            genno_export_folder = qw.QFileDialog.getExistingDirectory(
                self, self.app.translate("Choose Genno export folder")
            )
            if genno_export_folder:
                self.app.save_user_prefs({"genno_export_folder": genno_export_folder})
            else:
                qw.QMessageBox.warning(
                    self,
                    self.app.translate("Export"),
                    self.app.translate("No Genno export folder selected, aborting."),
                )
                return
        else:
            genno_export_folder = user_prefs["genno_export_folder"]

        genno_export_folder = Path(genno_export_folder)

    def on_back_to_validation_selection(self):
        query_manager_component: qm.QueryManagerComponent = self.app.get_component(
            "query_manager"
        )
        # Close all queries, replace with the final one
        query_manager_component.clear()

        self.widget_holder.set_current_widget("validation_selection")

        # Broadcast that we are back to validation selection
        self.broadcast.emit(
            "back_to_validation_selection",
            "validation_manager",
            self.instance_name,
            {},
        )

    def add_variants_to_validation(self, validation_infos: list[dict]):
        for validation_info in validation_infos:
            self.validation_model.insert_validation_data(**validation_info)

        self.broadcast.emit(
            "validation_infos_added",
            "validation_manager",
            self.instance_name,
            {"validation_infos": validation_infos},
        )

    def generic_receiver(
        self, action, sender_component_name, sender_instance_name, payload
    ):
        if action == "datalake_path_changed":
            self.validation_selection_widget.on_datalake_changed()
        if action == "add_variant_to_validation":
            if "validation_infos" in payload:
                self.add_variants_to_validation(payload["validation_infos"])

    def get_datalake(self) -> Union[dl.Datalake, None]:
        return self.app.get_component("datalake", "datalake")

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
