import logging
from functools import partial
from typing import Optional
from uuid import uuid4

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

    query_renamed = qc.Signal(str, str)

    def __init__(self, parent: qw.QWidget = None):
        super().__init__(parent)

        self._layout = qw.QVBoxLayout(self)
        self.query_list_view = qw.QListView(self)

        self._layout.addWidget(self.query_list_view)

        self.model = None

        self.setLayout(self._layout)

    def set_model(self, model: qc.QAbstractItemModel):
        self.model = model
        if self.query_list_view.model():
            self.query_list_view.selectionModel().currentChanged.disconnect()
        self.query_list_view.setModel(model)
        self.query_list_view.selectionModel().currentChanged.connect(
            self.on_current_query_changed
        )

    def set_current_query(self, query_instancename: str):
        if self.model:
            self.query_list_view.selectionModel().select(
                self.query_list_view.model().match(
                    self.query_list_view.model().index(0, 0),
                    qc.Qt.ItemDataRole.UserRole,
                    query_instancename,
                    1,
                    qc.Qt.MatchFlag.MatchExactly,
                )[0],
                qc.QItemSelectionModel.SelectionFlag.ClearAndSelect,
            )

    def on_current_query_changed(self, current: qc.QModelIndex, _: qc.QModelIndex):
        if not current:
            return
        if not current.isValid():
            return
        # Either None or empty string
        if not current.data(qc.Qt.ItemDataRole.UserRole):
            return
        self.current_query_changed.emit(current.data(qc.Qt.ItemDataRole.UserRole))


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

        # Map UI names to instance names for quick access
        self.query_uiname_toinstancename = {}

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

    def new_query(self, query_ui_name: str, data_prep: dict, query_options: dict):

        query_instancename = str(uuid4())
        query: q.QueryComponent = self.app.instantiate_component(
            "query",
            query_instancename,
        )

        query.set_ui_name(query_ui_name)

        query.setup_query(
            data_prep,
            query_options["table_uuid"],
            query_options["parquet_files"],
            query_options["gene_names"],
            query_options["sample_names"],
        )

        query_item = qg.QStandardItem(query_ui_name)
        query_item.setData(query_instancename, qc.Qt.ItemDataRole.UserRole)
        query_item.setEditable(False)

        self.query_model.appendRow(query_item)

        # COMPONENT HOLDERS INSTALLATION

        self.queries_tab_widget.blockSignals(True)
        self.app.window().add_component_to_window(query, mw.WindowRegion.UPPER)

        self.queries[query_instancename] = query
        self.query_uiname_toinstancename[query_ui_name] = query_instancename

        self.queries_tab_widget.blockSignals(False)

        # Connect title changed signal to update model only if widget exists
        if query.widget():
            query.widget().windowTitleChanged.connect(
                partial(self.update_query_ui_name, query_ui_name)
            )
        else:
            LOGGER.warning(
                f"Query {query_instancename} has no widget, cannot connect windowTitleChanged"
            )

        query.commit()
        self.set_current_query(query_instancename)
        return query

    def update_query_ui_name(self, old_name: str, new_name: str):
        """Update query name in model and queries dictionary"""

        if old_name == new_name:
            LOGGER.debug("Old name and new name are the same, no update needed.")
            return

        if new_name in self.query_uiname_toinstancename:
            LOGGER.warning(
                f"Query with UI name {new_name} already exists, cannot update {old_name} to {new_name}."
            )
            return

        query_instancename = self.query_uiname_toinstancename.get(old_name)
        if query_instancename is None:
            LOGGER.warning(
                f"Query with UI name {old_name} not found in queries dictionary."
            )
            return

        # Update the query's UI name
        query: "q.QueryComponent" = self.queries.get(query_instancename)
        if query is None:
            LOGGER.warning(
                f"Query with instance name {query_instancename} not found in queries dictionary."
            )
            return
        query.set_ui_name(new_name)

        # Update model
        items = self.query_model.findItems(old_name)
        if items:
            item = items[0]
            item.setText(new_name)

    def get_final_query(self):
        return self.queries.get(
            self.query_uiname_toinstancename.get(self.app.translate("Final validation"))
        )

    def get_query_model(self):
        return self.query_model

    def set_current_query(self, query_instancename: str):
        if query_instancename not in self.queries:
            return

        if (
            self.current_query
            and self.current_query.get_instance_name() == query_instancename
        ):
            # Avoid infinite recursion
            LOGGER.debug(
                f"Current query {self.current_query.get_instance_name()} is already set to {query_instancename}, no change needed."
            )
            return

        self.current_query: q.QueryComponent = self.queries[query_instancename]

        if self.current_query is None:
            LOGGER.warning(
                f"Current query is None, cannot set current query to {query_instancename}"
            )
            return

        query_tab_index = self.queries_tab_widget.indexOf(self.current_query.widget())
        if query_tab_index < 0:
            LOGGER.warning(
                f"Query {query_instancename} not found in queries tab widget, cannot set current query."
            )
            self.current_query = None
            return
        else:
            self.queries_tab_widget.setCurrentIndex(query_tab_index)
            self.query_manager_widget.set_current_query(query_instancename)
            LOGGER.debug(
                f"Setting current query to {self.current_query.get_instance_name()} - AKA {self.current_query.get_ui_name()}"
            )
        self.app.update_app(
            {
                "action": "selected_query_changed",
                "sender_component_name": self.component_name,
                "sender_instance_name": self.instance_name,
                "data": {
                    "current_query": (
                        self.current_query.get_instance_name()
                        if self.current_query
                        else None
                    ),
                },
            }
        )

    def close_query(self, query: q.QueryComponent):

        # Simply close the component - cleanup will be handled by beingDestroyed signal
        # Skip if model has been cleaned up
        if self.query_model is None:
            return

        query_ui_name = query.get_ui_name()

        # Remove from model
        items = self.query_model.findItems(query_ui_name)
        if items:
            self.query_model.removeRow(items[0].row())
        else:
            LOGGER.warning("Could not find query in model: %s", query_ui_name)

        query_name = query.get_instance_name()

        # Remove from queries dictionary
        if query_name in self.queries:
            del self.queries[query_name]
            del self.query_uiname_toinstancename[query_ui_name]

        if query is self.current_query:
            self.current_query = None

        query.close_component()

    def on_query_tab_changed(self, tab_index: int):
        if tab_index < 0:
            return

        current_query_ui_name = self.queries_tab_widget.tabText(tab_index)
        query: "q.QueryComponent" = self.queries.get(
            self.query_uiname_toinstancename.get(current_query_ui_name)
        )

        # Tab index changed but not its content (for example, the tab was moved)
        if (
            self.current_query
            and current_query_ui_name == self.current_query.get_ui_name()
        ):
            return

        self.set_current_query(query.get_instance_name())

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
