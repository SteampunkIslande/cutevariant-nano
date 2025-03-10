from typing import Union

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import app as ap
import app_manager.app_manager_component as am
import mainwindow as mw
import query.query_component as q


class QueryManagerWidget(qw.QWidget):

    current_query_changed = qc.Signal(str)

    def __init__(self, parent: qw.QWidget = None):
        super().__init__(parent)

        self._layout = qw.QVBoxLayout(self)
        self.query_list_view = qw.QListView(self)

        self._layout.addWidget(self.query_list_view)
        self.setLayout(self._layout)

    def set_model(self, model: qc.QAbstractItemModel):
        if self.query_list_view.model():
            self.query_list_view.selectionModel().currentChanged.disconnect()
        self.query_list_view.setModel(model)
        self.query_list_view.selectionModel().currentChanged.connect(
            self.on_current_query_changed
        )

    def on_current_query_changed(self, current: qc.QModelIndex, _: qc.QModelIndex):
        if not current.isValid():
            return
        # Either None or empty string
        if not current.data(qc.Qt.ItemDataRole.DisplayRole):
            return
        self.current_query_changed.emit(current.data(qc.Qt.ItemDataRole.DisplayRole))


class QueryManagerComponent(ap.AppComponent):

    def __init__(
        self, app: ap.App, instance_name: str, parent_component: ap.AppComponent
    ):
        super().__init__(app, instance_name, parent_component)

        self.queries: dict[str, q.QueryComponent] = {}

        self.current_query = None

        app_manager: am.AppManager = self.app.get_component("app-manager")

        self.variant_info_holder = app_manager.variant_info_holder
        self.genotype_info_holder = app_manager.genotype_info_holder

        self.fields_holder = app_manager.fields_widget_holder
        self.filters_holder = app_manager.filters_widget_holder

        self.query_model = qg.QStandardItemModel(self)
        self.query_manager_widget = QueryManagerWidget()
        self.query_manager_widget.set_model(self.query_model)
        self.query_manager_widget.current_query_changed.connect(self.set_current_query)

        self.queries_tab_widget = app.window().get_window_panel(mw.WindowRegion.UPPER)
        if self.queries_tab_widget:
            self.queries_tab_widget.currentChanged.connect(self.on_query_tab_changed)

    def new_query(self, query_name: str, data_prep: dict, query_options: dict):

        query: q.QueryComponent = self.app.instantiate_component(
            "query", query_name, self
        )

        print(query_options)

        query.setup_query(data_prep).set_editable_table_name(
            query_options["table_uuid"]
        ).set_readonly_table(query_options["parquet_files"]).set_selected_genes(
            query_options["gene_names"]
        ).set_selected_samples(
            query_options["sample_names"]
        ).commit()

        self.query_model.appendRow(qg.QStandardItem(query_name))

        # COMPONENT HOLDERS INSTALLATION
        self.fields_holder.add_component(query.get_fields_component())
        self.filters_holder.add_component(query.get_filters_component())

        self.queries_tab_widget.blockSignals(True)
        self.app.window().add_component_to_window(query, mw.WindowRegion.UPPER)
        self.queries[query_name] = query
        self.queries_tab_widget.blockSignals(False)

        self.set_current_query(query_name)

    def get_query_model(self):
        return self.query_model

    def set_current_query(self, query_name: str):

        self.queries_tab_widget.setCurrentIndex(
            self.queries_tab_widget.indexOf(self.queries[query_name].widget())
        )

    def close_query(self, query: q.QueryComponent):
        tab_index = self.queries_tab_widget.indexOf(query.widget())

        if tab_index >= 0:
            # Remove all the components that the specified query has installed
            self.queries_tab_widget.removeTab(tab_index)

        # COMPONENT HOLDERS UNINSTALLATION
        self.fields_holder.remove_component(
            query.get_fields_component().get_instance_name()
        )
        self.filters_holder.remove_component(
            query.get_filters_component().get_instance_name()
        )

    def on_query_tab_changed(self, tab_index: int):
        if tab_index < 0:
            return

        current_query_name = self.queries_tab_widget.tabText(tab_index)

        # Tab index changed, but not its content
        if (
            self.current_query
            and current_query_name == self.current_query.get_instance_name()
        ):
            return

        self.current_query = self.queries[current_query_name]

        # self.variant_info_holder.set_current_component(
        #     self.current_query.get_variant_info().get_instance_name()
        # )

        # COMPONENT HOLDERS UPDATE
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

    def widget(self) -> qw.QWidget:
        return self.query_manager_widget

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
        for _, query in self.queries.items():
            self.close_query(query)
        self.query_model.clear()


def register_component():
    return "query_manager", {
        "instantiation_policy": "singleton",
        "instantiate_on": "demand",
        "class": QueryManagerComponent,
    }
