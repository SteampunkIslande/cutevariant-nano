import logging
from typing import Optional

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import app as ap
import mainwindow as mw
import query.query_component as q
from component_registry import register_app_component

LOGGER = logging.getLogger(__name__)


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


@register_app_component(
    name="query_manager", policy="singleton", instantiation_time="setup"
)
class QueryManagerComponent(ap.AppComponent):

    component_name = "query_manager"

    def __init__(self, app: ap.App, instance_name: str):
        super().__init__(app, instance_name)
        LOGGER.debug(
            f"Instantiating QueryManagerComponent with instance name: {instance_name}"
        )

        # Store QueryComponent references in a regular dictionary
        self.queries = {}

        self.current_query: Optional[q.QueryComponent] = None

        self.query_model = qg.QStandardItemModel(self)
        self.query_manager_widget = QueryManagerWidget()
        self.query_manager_widget.set_model(self.query_model)
        self.query_manager_widget.current_query_changed.connect(self.set_current_query)

        self.queries_tab_widget = app.window().get_window_panel(mw.WindowRegion.UPPER)
        if self.queries_tab_widget:
            self.queries_tab_widget.currentChanged.connect(self.on_query_tab_changed)

        # Note: ComponentRegistry doesn't have componentDestroyed signal
        # Component destruction management is done via the beingDestroyed signal of QueryComponent

    def new_query(self, query_name: str, data_prep: dict, query_options: dict):

        query: q.QueryComponent = self.app.instantiate_component("query", query_name)

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

        # Connect title changed signal to update model only if widget exists
        if query.widget():
            query.widget().windowTitleChanged.connect(
                lambda title: self._update_query_name(query_name, title)
            )
        else:
            LOGGER.warning(
                f"Query {query_name} has no widget, cannot connect windowTitleChanged"
            )

        query.commit()
        self.set_current_query(query_name)
        return query

    def _update_query_name(self, old_name: str, new_name: str):
        """Update query name in model and queries dictionary"""
        if old_name not in self.queries:
            return

        # Update model
        items = self.query_model.findItems(old_name)
        if items:
            item = items[0]
            item.setText(new_name)

        # Update dictionary
        query = self.queries.pop(old_name)
        self.queries[new_name] = query

    def get_final_query(self):
        return self.queries.get(self.app.translate("Final validation"))

    def get_query_model(self):
        return self.query_model

    def set_current_query(self, query_name: str):
        if query_name not in self.queries:
            return

        self.queries_tab_widget.setCurrentIndex(
            self.queries_tab_widget.indexOf(self.queries[query_name].widget())
        )
        self.current_query = self.queries[query_name]

        LOGGER.debug(
            f"Setting current query to {self.current_query.get_instance_name()}"
        )
        self.app.update_app(
            {
                "action": "selected_query_changed",
                "sender_component_name": self.component_name,
                "sender_instance_name": self.instance_name,
                "data": {
                    "current_query": self.current_query.get_instance_name(),
                },
            }
        )

    def close_query(self, query: q.QueryComponent):

        # Simply close the component - cleanup will be handled by beingDestroyed signal
        # Skip if model has been cleaned up
        if self.query_model is None:
            return

        query_name = query.get_instance_name()

        # Remove from model
        items = self.query_model.findItems(query_name)
        if items:
            self.query_model.removeRow(items[0].row())
        else:
            LOGGER.warning("could not find query in model:", query_name)

        # Remove from queries dictionary
        if query_name in self.queries:
            del self.queries[query_name]

        if query is self.current_query:
            self.current_query = None

        query.close_component()

    def on_query_tab_changed(self, tab_index: int):
        if tab_index < 0:
            return

        current_query_name = self.queries_tab_widget.tabText(tab_index)

        # Tab index changed but not its content (for example, the tab was moved)
        if (
            self.current_query
            and current_query_name == self.current_query.get_instance_name()
        ):
            return

        self.set_current_query(current_query_name)

        # # Only emit signal if current_query is not None
        # if self.current_query:
        #     self.broadcast.emit(
        #         "current_query_changed",
        #         "query_manager",
        #         self.instance_name,
        #         {"current_query": self.current_query.get_instance_name()},
        #     )

    def widget(self) -> qw.QWidget:
        return self.query_manager_widget

    def on_datalake_changed(self):
        return

    def clear(self):
        # Close all
        queries = list(self.queries.values())
        for query in queries:
            self.close_query(query)
        del queries
        self.query_model.clear()

    def close_component(self):
        # Close all queries
        self.clear()
        self.query_manager_widget = None
        self.query_model = None

        # Call parent close_component
        super().close_component()
