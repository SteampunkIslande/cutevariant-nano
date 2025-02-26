from typing import Union

import duckdb as db
import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import app as ap
from common_widgets.multiwidget_holder import MultiWidgetHolder
from datalake.datalake_component import Datalake
from validation_manager.validation_selection_widget import ValidationSelectionWidget
from validation_manager.validation_widget import ValidationWidget


def finish_validation(conn: db.DuckDBPyConnection, table_uuid: str):
    conn.sql(
        f"UPDATE validations SET completed = TRUE WHERE table_uuid = '{table_uuid}'"
    )


class ValidationManagerComponent(ap.AppComponent):

    def __init__(
        self, app: ap.App, instance_name: str, parent_component: ap.AppComponent
    ):
        super().__init__(app, instance_name, parent_component)
        self.app = app
        self.instance_name = instance_name
        self.parent_component = parent_component

        self.datalake: Datalake = app.get_component("datalake")

        self.datalake.folder_changed.connect(self.on_datalake_changed)

        self.widget_holder = MultiWidgetHolder()

        self.validation_selection_widget = ValidationSelectionWidget(
            self.app, self.datalake
        )
        self.validation_widget = ValidationWidget(self.app, self.datalake)

        self.widget_holder.add_widget(
            self.validation_selection_widget, "validation_selection"
        )
        self.widget_holder.add_widget(self.validation_widget, "validation")

        self.widget_holder.set_current_widget("validation_selection")

        self.widget_holder.setWindowTitle("Validation selection")

    def on_validation_select(self):
        validation = self.validation_selection_widget.get_selected_validation()
        # self.validation_widget.

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
