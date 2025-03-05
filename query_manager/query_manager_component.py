from typing import Union

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import app as ap
import app_manager.app_manager_component as am
import mainwindow as mw
import query.query_component as q


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

        app_manager: am.AppManager = self.app.get_component("app-manager")

        self.variant_info_holder = app_manager.variant_info_holder
        self.genotype_info_holder = app_manager.genotype_info_holder

        self.fields_holder = app_manager.fields_widget_holder
        self.filters_holder = app_manager.filters_widget_holder

        self.validations_method = None

        self.query_model = qg.QStandardItemModel(self)

        self.queries_tab_widget = app.window().get_window_panel(mw.WindowRegion.UPPER)

    def new_query(self, query_name: str):

        if query_name in self.queries:
            return False

        query: q.QueryComponent = self.app.instantiate_component(
            "query", f"query.{query_name}", self
        )

        tab_index = self.app.window().add_component_to_window(
            query, mw.WindowRegion.UPPER
        )
        self.queries[tab_index] = query
        self.query_model.appendRow(qg.QStandardItem(query_name))

        self.fields_holder.add_component(query.get_fields_component())
        self.filters_holder.add_component(query.get_filters_component())

    def get_query_model(self):
        return self.query_model

    def set_current_query(self, query_name: str):
        for tab_index, query in self.queries.items():
            if query.get_instance_name() == query_name:
                self.queries_tab_widget.setCurrentIndex(tab_index)
                return

    def close_query(self, tab_index: int):
        # Remove all the components that the specified query has installed
        self.queries_tab_widget.removeTab(tab_index)
        query = self.queries[tab_index]

        self.query_model.removeRow(
            self.query_model.findItems(query.get_instance_name())[0].row()
        )

        # TODO: Remove query fields component from the component holders

        print("Closing query", query.get_instance_name())

    def on_query_tab_changed(self, tab_index: int):
        if tab_index not in self.queries:
            print("Shouldn't be possible...")
            return

        self.current_query = self.queries[tab_index]

        # self.variant_info_holder.set_current_component(
        #     self.current_query.get_variant_info().get_instance_name()
        # )
        self.fields_holder.set_current_component(
            self.current_query.get_fields_component().get_instance_name()
        )
        self.filters_holder.set_current_component(
            self.current_query.get_filters_component().get_instance_name()
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

    def clear(self):
        # Close all
        for tab_index in self.queries:
            self.close_query(tab_index)
        self.query_model.clear()


def register_component():
    return "query_manager", {
        "instantiation_policy": "singleton",
        "instantiate_on": "demand",
        "class": QueryManagerComponent,
    }
