import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import app as ap
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
        if not current:
            return
        if not current.isValid():
            return
        # Either None or empty string
        if not current.data(qc.Qt.ItemDataRole.DisplayRole):
            return
        self.current_query_changed.emit(current.data(qc.Qt.ItemDataRole.DisplayRole))


class QueryManagerComponent(ap.AppComponent):

    component_name = "query-manager"

    def __init__(self, app: ap.App, instance_name: str):
        super().__init__(app, instance_name)

        self.queries: dict[str, q.QueryComponent] = {}

        self.current_query = None

        self.query_model = qg.QStandardItemModel(self)
        self.query_manager_widget = QueryManagerWidget()
        self.query_manager_widget.set_model(self.query_model)
        self.query_manager_widget.current_query_changed.connect(self.set_current_query)

        self.queries_tab_widget = app.window().get_window_panel(mw.WindowRegion.UPPER)
        if self.queries_tab_widget:
            self.queries_tab_widget.currentChanged.connect(self.on_query_tab_changed)

    def new_query(self, query_name: str, data_prep: dict, query_options: dict):

        query: q.QueryComponent = self.app.instantiate_component(
            "query", f"{self.instance_name}/{query_name}"
        )

        query.setup_query(
            data_prep,
            query_options["table_uuid"],
            query_options["parquet_files"],
            query_options["gene_names"],
            query_options["sample_names"],
        )
        self.query_model.appendRow(qg.QStandardItem(query_name))

        # COMPONENT HOLDERS INSTALLATION

        self.queries_tab_widget.blockSignals(True)
        self.app.window().add_component_to_window(query, mw.WindowRegion.UPPER)
        self.queries[query_name] = query
        self.queries_tab_widget.blockSignals(False)

        query.commit()
        self.set_current_query(query_name)
        return query

    def get_final_query(self):
        return self.queries.get(self.app.translate("Final validation"))

    def get_query_model(self):
        return self.query_model

    def set_current_query(self, query_name: str):

        self.queries_tab_widget.setCurrentIndex(
            self.queries_tab_widget.indexOf(self.queries[query_name].widget())
        )
        self.current_query = self.queries[query_name]

    def close_query(self, query: q.QueryComponent):

        if query is self.current_query:
            self.current_query = None
        query.close()

    def on_query_tab_changed(self, tab_index: int):
        if tab_index < 0:
            return

        current_query_name = self.queries_tab_widget.tabText(tab_index)

        # Tab index changed but not its content (for example, the tab was moved)
        if (
            self.current_query
            and current_query_name
            == self.current_query.get_instance_name().split("/")[-1]
        ):
            return

        self.set_current_query(current_query_name)

        self.broadcast.emit(
            "current_query_changed",
            "query_manager",
            self.instance_name,
            {"current_query": self.current_query.get_instance_name()},
        )

    def widget(self) -> qw.QWidget:
        return self.query_manager_widget

    def on_datalake_changed(self):
        return

    def clear(self):
        # Close all
        queries = list(self.queries.values())
        self.queries = dict()
        for query in queries:
            self.close_query(query)
        self.query_model.clear()


def register_component():
    return QueryManagerComponent.component_name, {
        "instantiation_policy": "singleton",
        "instantiate_on": "demand",
        "class": QueryManagerComponent,
    }
