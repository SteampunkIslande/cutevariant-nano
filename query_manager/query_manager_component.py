import json
import logging
from functools import partial
from pathlib import Path
from typing import Optional
from uuid import uuid4

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import app as ap
import datalake.datalake_component as dl
import mainwindow as mw
import query.query_component as q
from commons import yaml_load
from component_registry import register_app_component
from query_manager.query_manager_widget import QueryManagerWidget

LOGGER = logging.getLogger(__name__)


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
        self.query_manager_widget = QueryManagerWidget(self.query_model)
        self.query_manager_widget.current_query_changed.connect(self.set_current_query)

        self.queries_tab_widget = app.window().get_window_panel(mw.WindowRegion.UPPER)
        if self.queries_tab_widget:
            self.queries_tab_widget.currentChanged.connect(self.on_query_tab_changed)

        # Initialize datalake component and path
        self.datalake_path = None

        self.group_name = self.app.translate("Generic Queries")

        # Note: ComponentRegistry doesn't have componentDestroyed signal
        # Component destruction management is done via the beingDestroyed signal of QueryComponent

    def on_start(self):
        self.datalake: dl.DatalakeComponent = self.app.get_component("datalake")
        self.app.datalake_path_changed.connect(self.on_datalake_changed)
        if self.datalake:
            self.datalake_path = self.datalake.datalake_path

    def set_group_name(self, group_name: str):
        """Set the group name for the queries"""
        self.group_name = group_name

    def new_generic_query(
        self,
        ui_name: str,
        query_definition: dict = None,
        readonly_files: list = None,
        editable_table_name: str = None,
        **kwargs,  # Additional parameters for specific use (e.g., selected_genes, selected_samples)
    ):

        serialized_path = (
            (
                Path(self.datalake_path)
                / "queries"
                / self.group_name
                / (ui_name + ".json")
            )
            if self.datalake_path
            else None
        )

        if serialized_path and serialized_path.exists():
            # Read from this json the query instance name
            serialized_query = yaml_load(serialized_path)
            query_instancename = serialized_query["instance_name"]
            query: q.QueryComponent = self.app.instantiate_component(
                "query",
                query_instancename,
            )

            query.from_json(
                serialized_query,
            )

        else:
            if not query_definition:
                raise ValueError("Template must be provided for new generic queries.")
            if not readonly_files:
                raise ValueError(
                    "Parquet files must be provided for new generic queries."
                )
            query_instancename = str(uuid4())
            query: q.QueryComponent = self.app.instantiate_component(
                "query",
                query_instancename,
            )

            query.set_ui_name(ui_name)
            query.setup_query(
                query_definition,
                editable_table_name,
                readonly_files,
                **kwargs,  # Pass additional parameters like selected_genes, selected_samples
            )

        query_item = qg.QStandardItem(ui_name)
        query_item.setData(query_instancename, qc.Qt.ItemDataRole.UserRole)
        query_item.setEditable(False)

        self.query_model.appendRow(query_item)

        # COMPONENT HOLDERS INSTALLATION

        self.queries_tab_widget.blockSignals(True)
        self.app.window().add_component_to_window(query, mw.WindowRegion.UPPER)

        self.queries[query_instancename] = query
        self.query_uiname_toinstancename[ui_name] = query_instancename

        self.queries_tab_widget.blockSignals(False)

        # Connect title changed signal to update model only if widget exists
        if query.widget():
            query.widget().windowTitleChanged.connect(
                partial(self.update_query_ui_name, ui_name)
            )
        else:
            LOGGER.warning(
                f"Query {query_instancename} has no widget, cannot connect windowTitleChanged"
            )

        query.commit()
        self.set_current_query(query_instancename)
        return query

    def update_query_definition(self, query: q.QueryComponent, new_definition: dict):
        """Update the query definition of an existing query"""
        if query.get_instance_name() not in self.queries:
            LOGGER.warning(
                f"Query with instance name {query.get_instance_name()} not found in queries dictionary."
            )
            return
        query.setup_query_template(new_definition).compute_fields().commit()

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

        self.serialize_query(
            query,
            query_group_name=self.group_name,
            query_ui_name=query.get_ui_name(),
        )

        query.close_component()

    def serialize_query(
        self,
        query: "q.QueryComponent",
        query_group_name: str,
        query_ui_name: str,
    ):
        """Serialize the current query to a JSON file in the datalake queries folder."""
        if not self.datalake_path:
            LOGGER.error("Datalake path is not set, cannot serialize query.")
            return

        serialized_path = (
            Path(self.datalake_path)
            / "queries"
            / query_group_name
            / (query_ui_name + ".json")
        )

        serialized_path.parent.mkdir(parents=True, exist_ok=True)

        with open(serialized_path, "w") as f:
            json.dump(
                query.to_json(),
                f,
                indent=4,
                ensure_ascii=False,
            )

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
        """Handle datalake path changes"""
        if self.datalake:
            self.datalake_path = self.datalake.datalake_path
            LOGGER.debug(f"Datalake path changed to: {self.datalake_path}")
        else:
            LOGGER.warning("Datalake component not found, cannot update datalake path.")
            self.datalake_path = None
        return

    # def save_to_session(self):
    #     return {
    #         "group_name": self.group_name,
    #         "datalake_path": self.datalake_path,
    #     }

    # def load_from_session(self, session: dict):
    #     """Load the component state from a session dictionary."""

    #     datalake_path = session.get("datalake_path", None)
    #     if not datalake_path:
    #         return
    #     self.datalake_path = datalake_path

    #     if "group_name" in session:
    #         self.set_group_name(session["group_name"])
    #     else:
    #         LOGGER.warning("No group name found in session, using default.")
    #         self.set_group_name(self.app.translate("Generic Queries"))

    #     # Search for queries from self.group_name within datalake path/queries/group_name
    #     queries_path = Path(self.datalake_path) / "queries" / self.group_name
    #     if not queries_path.exists():
    #         LOGGER.warning(
    #             f"Queries path {queries_path} does not exist, no queries to load."
    #         )
    #         return
    #     for query_file in queries_path.glob("*.json"):
    #         with open(query_file, "r") as f:
    #             serialized_query: dict = json.load(f)
    #         if "ui_name" not in serialized_query:
    #             serialized_query["ui_name"] = query_file.stem
    #         self.new_generic_query(**serialized_query)

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

        # Call parent close_component
        super().close_component()
