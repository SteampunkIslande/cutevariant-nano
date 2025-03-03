from typing import Union

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import app as ap
import mainwindow as mw
import query.query_component as q
import app_manager.app_manager_component as am


class QueryManagerComponent(ap.AppComponent):

    def __init__(
        self, app: ap.App, instance_name: str, parent_component: ap.AppComponent
    ):
        super().__init__(app, instance_name, parent_component)
        self.app = app
        self.instance_name = instance_name
        self.parent_component = parent_component

        self.queries: dict[int, q.QueryComponent] = {}

        self.current_query = None

        app_manager: am.AppManager = self.app.get_component("app_manager")

        self.variant_info_holder = app_manager.variant_info_holder
        self.genotype_info_holder = app_manager.genotype_info_holder

        self.fields_holder = app_manager.fields_widget_holder
        self.filters_holder = app_manager.filters_widget_holder

        self.queries_tab_widget = app.window().get_window_panel(mw.WindowRegion.UPPER)

    def new_query(self, query_name: str, query_definition: dict):
        if query_name in self.queries:
            return False

        query: q.QueryComponent = self.app.instantiate_component(
            "query", f"query.{query_name}", self
        )
        tab_index = self.app.window().add_component_to_window(
            query, mw.WindowRegion.UPPER
        )
        self.queries[tab_index] = query

        # Update components that should be attached to

    def close_query(self, query_name: str):
        # Remove all the components that the specified query has installed
        pass

    def on_query_tab_changed(self, tab_index: int):
        if tab_index not in self.queries:
            print("Shouldn't be possible...")
            return

        self.current_query = self.queries[tab_index]

        self.variant_info_holder.set_current_component(
            self.current_query.variant_info_component().get_instance_name()
        )

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
        return None

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

    def close(self):
        pass


def register_component():
    return "query_manager", {
        "instantiation_policy": "singleton",
        "instantiate_on": "demand",
        "class": QueryManagerComponent,
    }
