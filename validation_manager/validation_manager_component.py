import logging
import os
from functools import partial
from pathlib import Path

# Deferred import to resolve circular dependency
from typing import Union

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import app as ap
import datalake.datalake_component as dl
import query_manager.query_manager_component as qm
from common_widgets.multiwidget_holder import MultiWidgetHolder
from commons import yaml_load
from component_registry import register_app_component

LOGGER = logging.getLogger(__name__)


@register_app_component(
    name="validation_manager", policy="singleton", instantiation_time="demand"
)
class ValidationManagerComponent(ap.AppComponent):

    component_name = "validation_manager"

    def __init__(self, app: ap.App, instance_name: str):
        super().__init__(app, instance_name)

        self.widget_holder = MultiWidgetHolder()
        # Deferred local import
        from validation_manager.validation_model import ValidationModel

        self.validation_model = ValidationModel(self.app, self)

        from validation_manager.validation_selection_widget import (
            ValidationSelectionWidget,
        )
        from validation_manager.validation_widget import ValidationWidget

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

        self.query_manager_component: qm.QueryManagerComponent = self.app.get_component(
            "query_manager"
        )

        # Make sure to update self if the datalake changes
        self.app.datalake_path_changed.connect(
            self.validation_selection_widget.on_datalake_changed
        )

        self.app.subscribe_to_contextmenu(self, "query_table_widget")

        self.validation_method = None
        self.validation_method_name = None

    def on_validation_start(self):
        validation_info = self.validation_selection_widget.get_selected_validation()
        self.widget_holder.set_current_widget("validation")

        self.set_validation(validation_info)

    def init_validation(self, validation_info: dict):
        self.sample_names = validation_info.get("sample_names")
        validation_method = validation_info.get("validation_method")
        if not validation_method:
            return
        config_folder = self.app.get_config_folder()

        self.validation_method_name = validation_method
        self.validation_method = yaml_load(
            os.path.join(
                config_folder, "validation_methods", validation_method + ".yaml"
            )
        )

        self.table_uuid = validation_info.get("table_uuid")
        self.gene_names = validation_info.get("gene_names")
        self.parquet_files = validation_info.get("parquet_files")

        self.validation_name = validation_info.get("validation_name")

    def set_validation(self, validation_info: dict):

        self.query_manager_component.clear()
        self.init_validation(validation_info)

        self.query_manager_component.set_group_name(self.table_uuid)

        # Add final validation query
        # validation_mismatches = {}
        self.query_manager_component.new_generic_query(
            self.app.translate("Final validation"),
            self.validation_method["final"]["query"],
            readonly_files=self.parquet_files,
            editable_table_name=self.table_uuid,
            **{
                "selected_samples": self.sample_names,
                "selected_genes": self.gene_names,
            },
        )

        completed = validation_info.get("completed")
        if completed:
            self.validation_widget.set_completed(True)
            return

        for sample_name in self.sample_names:
            self.query_manager_component.new_generic_query(
                sample_name,
                self.validation_method["default"]["query"],
                readonly_files=self.parquet_files,
                editable_table_name=self.table_uuid,
                **{
                    "selected_samples": [sample_name],
                    "selected_genes": self.gene_names,
                },
            )

    def validate(self):

        # Close all queries, replace with the final one
        self.query_manager_component.clear()
        self.query_manager_component.new_generic_query(
            self.app.translate("Final validation"),
            self.validation_method["final"]["query"],
            readonly_files=self.parquet_files,
            editable_table_name=self.table_uuid,
            **{
                "sample_names": self.sample_names,
                "gene_names": self.gene_names,
            },
        )
        self.validation_model.finish_validation(self.table_uuid)

    def export_to_genno(self):
        if not self.validation_method:
            return

        user_prefs = self.app.get_user_prefs()
        if "genno_export_folder" not in user_prefs:
            qw.QMessageBox.warning(
                self.widget(),
                self.app.translate("Export"),
                self.app.translate(
                    "No Genno export folder selected, please choose one."
                ),
            )
            genno_export_folder = qw.QFileDialog.getExistingDirectory(
                self.widget(), self.app.translate("Choose Genno export folder")
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

        query = self.query_manager_component.get_final_query()
        if not query:
            LOGGER.warning("No query to export")
            return
        sql_query = query.select_query(paginated=False, columns="COLUMNS('^[^.]')")
        datalake = self.get_datalake()
        if not datalake:
            LOGGER.error("Datalake component is not available, cannot export to genno")
            return

        base_filename = self.validation_name or "validation"
        datalake.run_with_connection(
            "validation",
            lambda conn: conn.sql(
                f""" COPY ({sql_query}) TO '{genno_export_folder / f'{base_filename}.csv'}' (DELIMITER ';') """
            ),
        )

    def on_back_to_validation_selection(self):
        self.query_manager_component.clear()
        self.widget_holder.set_current_widget("validation_selection")

    def add_variants_to_validation(self, payload: dict[str, dict[dict[str, str]]]):
        if "data" not in payload:
            LOGGER.error("No data in payload to add variants to validation")
            return
        for row_data in payload["data"]:
            # row_data is the dict contained in each row of the query table
            # we have to enrich it with table_uuid, validation_hash, sample_name, run_name, transcript_iD, and variant_hash
            update_data = {
                "table_uuid": self.table_uuid,
                "validation_hash": row_data.get(".validation_hash"),
                "sample_name": row_data.get(".sample_name"),
                "run_name": row_data.get(".run_name"),
                "transcript_ID": row_data.get(".NM"),
                "variant_hash": row_data.get(".variant_hash"),
                "accepted": True,
            }

            self.validation_model.insert_validation_data(update_data)

    def get_datalake(self) -> Union[dl.DatalakeComponent, None]:
        return self.app.get_component("datalake", "datalake")

    def get_instance_name(self) -> str:
        return self.instance_name

    def load_from_session(self, session: dict):
        # Implement loading logic here

        validation_info = session.get("validation_info", {})
        if validation_info:
            self.widget_holder.set_current_widget("validation")
            self.set_validation(validation_info)

    def save_to_session(self) -> dict:
        # Implement saving logic here

        return {
            "validation_info": self.validation_selection_widget.serialize_validation_info()
        }

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

    def get_contextmenu_entries(
        self, producer_name: str, local_info: dict
    ) -> list[tuple[str, qg.QAction]]:
        if producer_name == "query_table_widget":
            add_to_validation_action = qg.QAction(
                self.app.translate("Add to validation")
            )
            add_variants_callback = partial(self.add_variants_to_validation, local_info)
            add_to_validation_action.triggered.connect(add_variants_callback)
            return [(self.app.translate("Validation/Genno"), add_to_validation_action)]
        return []

    def close_component(self):

        # Clean up resources
        self.validation_model = None
        self.validation_selection_widget = None
        self.validation_widget = None
        self.query_manager_component = None

        # Call parent close_component
        super().close_component()
