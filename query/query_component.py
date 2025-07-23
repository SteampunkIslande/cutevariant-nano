#!/usr/bin/env python

import logging
from math import ceil
from typing import List, Union

import duckdb as db
import PySide6.QtCore as qc

import app as ap
import datalake.datalake_component as dl
import filters.filters as flt
import query
import query.query_table_widget
from commons import duck_db_literal_string_list, duck_db_literal_string_tuple

LOGGER = logging.getLogger(__name__)


def validate_query_template(data: dict) -> bool:
    """Validate the query template structure."""
    if not isinstance(data, dict):
        return False
    if "select" not in data:
        return False
    select_def = data["select"]
    if not isinstance(select_def, dict):
        return False
    if "fields" not in select_def or not isinstance(select_def["fields"], list):
        return False
    if "tables" not in select_def or not isinstance(select_def["tables"], list):
        return False
    for table in select_def["tables"]:
        if not isinstance(table, dict):
            return False
        if "on" in table and not isinstance(table["on"], (str, dict)):
            return False
        if "how" in table and table["how"] not in ["INNER", "LEFT", "RIGHT", "FULL"]:
            return False
        if "select" in table and not validate_query_template(table["select"]):
            return False
    if "filter" in select_def and not isinstance(select_def["filter"], dict):
        return False
    if "group_by" in select_def and not isinstance(select_def["group_by"], (str, list)):
        return False
    if "order_by" in select_def and not isinstance(select_def["order_by"], list):
        return False
    for order in select_def.get("order_by", []):
        if not isinstance(order, dict) or "field" not in order or "order" not in order:
            return False
        if order["order"] not in ["ASC", "DESC"]:
            return False
    return True


def build_query_template(data: dict) -> str:
    select_def = data["select"]
    fields = select_def["fields"]
    result = ""
    tables = []
    for i, table_def in enumerate(select_def["tables"]):
        table_def: dict
        if "select" in table_def:
            expr_and_alias = (
                f"({build_query_template(table_def)}) {table_def.get('alias', '')}"
            )
        if "expression" in table_def:
            expr_and_alias = f"{table_def['expression']} {table_def.get('alias', '')}"

        tables.append(
            (
                expr_and_alias,
                table_def["on"] if i != 0 else None,
                table_def["how"] if i != 0 else None,
            )
        )

    result += f"SELECT {', '.join(fields)} FROM {tables[0][0]} "
    for table, on, how in tables[1:]:
        if isinstance(on, dict):
            on = str(flt.FilterItem.from_json(on))
        result += f" {how} JOIN {table} ON {on} "

    if "filter" in select_def:
        filter_def = select_def["filter"]
        filter_str = str(flt.FilterItem.from_json(filter_def))
        if filter_str:
            result += f" WHERE {filter_str} "

    if "group_by" in select_def:
        group_by = select_def["group_by"]
        if isinstance(group_by, list):
            group_by = ",".join(group_by)
        result += f" GROUP BY {group_by} "

    # order_by is a list of dicts with keys "field" and "order"
    if "order_by" in select_def:
        order_by = select_def["order_by"]
        result += " ORDER BY "
        result += ", ".join([f'{ob["field"]} {ob["order"]}' for ob in order_by])

    return result


def run_sql(query: str, conn: db.DuckDBPyConnection = None) -> Union[List[dict], None]:
    if not conn:
        res = db.sql(query).pl().to_dicts()
        if res:
            return res

    else:
        res = conn.sql(query)
        if res:
            return res.pl().to_dicts()


from component_registry import register_app_component


@register_app_component(name="query", policy="multi", instantiation_time="demand")
class QueryComponent(ap.AppComponent):

    component_name = "query"

    RESERVED_VARIABLES = [
        "main_table",
        "user_table",
        "pwd",
        "selected_genes",
        "selected_samples",
    ]

    # Signal for external use (tell the UI to update)
    query_changed = qc.Signal()

    def __init__(self, app: "ap.App", instance_name: str):
        super().__init__(app, instance_name)

        # Safer to init state before setting up the view
        self.init_state()

        self.view = query.query_table_widget.QueryTableWidget(self.app, self)
        self.closing.connect(self.view.close)

        self.ui_name = self.app.translate("Unnamed query")

    def get_ui_name(self) -> str:
        """Get the UI name of the query, used in the QueryManagerWidget."""
        return self.ui_name

    def set_ui_name(self, name: str):
        """Set the UI name of the query, used in the QueryManagerWidget."""
        self.ui_name = name
        self.view.setWindowTitle(name)
        return self

    def init_state(self):
        # When we create a new Query, we want to reset everything, except for the datalake path...
        self.query_template = ""
        self.query_definition: dict = {}

        # Order by, updated by the order_by_changed signal
        self.order_by = []

        # All fields available to the user. Including those starting with a dot (hidden by default in the UI).
        # Also includes fields that are not selected in the view. So that they can be filtered on.
        self.fields = []

        # Filter tree, updated by the filters_changed signal
        self.applied_filter = None

        # Essential members, not meant to change
        self.readonly_table = None
        self.readonly_files = []
        self.editable_table_name = None
        self.selected_samples = []
        self.selected_genes = []

        # Pagination limits
        self.limit = 10
        self.offset = 0

        # Pagination state
        self.current_page = 1
        self.page_count = 1

        # Data
        self.data = []
        self.header = []

        # User-defined variables
        self.variables = dict()

        # Datalake component, used to run queries
        self.datalake: dl.DatalakeComponent = self.app.get_component("datalake")

        return self

    # Variable management methods
    def add_variable(self, key: str, value: str):
        if key in QueryComponent.RESERVED_VARIABLES:
            raise ValueError(f"Variable name {key} is reserved")
        self.variables[key] = value
        return self

    def get_variable(self, key: str) -> str:
        return self.variables.get(key)

    def list_variables(self) -> List[str]:
        return list(self.variables.keys())

    def set_variable(self, key: str, value: str):
        if key in QueryComponent.RESERVED_VARIABLES:
            raise ValueError(f"Variable name {key} is reserved")
        self.variables[key] = value
        return self

    def remove_variable(self, key: str):
        if key in self.variables:
            del self.variables[key]
        return self

    def get_limit(self) -> int:
        return self.limit

    def set_limit(self, limit: int):
        self.limit = limit
        return self

    def get_page(self) -> int:
        return self.current_page

    def set_page(self, page: int):
        if page < 1:
            raise ValueError("Page number must be greater than 0")
        if page > self.page_count:
            raise ValueError("Page number exceeds total page count")
        self.current_page = page
        self.offset = (page - 1) * self.limit
        return self

    def previous_page(self):
        if self.current_page > 1:
            self.set_page(self.current_page - 1)
        return self

    def next_page(self):
        if self.current_page < self.page_count:
            self.set_page(self.current_page + 1)
        return self

    def first_page(self):
        self.set_page(1)
        return self

    def last_page(self):
        self.set_page(self.page_count)
        return self

    def get_page_count(self):
        return self.page_count

    # Those useless getters...
    def get_data(self):
        return self.data

    def get_header(self):
        return self.header

    def get_readonly_table(self) -> str:
        return self.readonly_table

    # Convenient method to set the readonly table from a list of files
    def set_readonly_table(self, files: List[str]):
        if not files:
            return self
        if not self.datalake:
            return self

        self.readonly_files = files

        if len(files) == 1:
            self.readonly_table = f"read_parquet('{self.datalake.datalake_path}/{files[0]}',union_by_name=True)"
        else:
            self.readonly_table = f"read_parquet({duck_db_literal_string_list(self.datalake.relative_to_absolute(f) for f in files)},union_by_name=True)"
        return self

    def get_column_info(self, colname: str):
        select = self.select_query(paginated=False, columns=f'"{colname}"')
        if not self.datalake:
            return
        (datatype, nullable) = self.datalake.run_with_connection(
            "validation",
            lambda conn: conn.sql(
                f"SELECT column_type,null FROM (describe({select}))"
            ).fetchone(),
        )
        top_10_values = self.datalake.run_with_connection(
            "validation",
            lambda conn: [
                c[1]
                for c in conn.sql(
                    f"""SELECT COUNT(*) AS count,"{colname}" FROM ({select}) GROUP BY "{colname}" ORDER BY count DESC LIMIT 10"""
                ).fetchall()
            ],
        )

        return {
            "name": colname,
            "type": datatype,
            "nullable": nullable,
            "top_10_values": top_10_values,
        }

    def get_editable_table_name(self) -> str:
        return self.editable_table_name

    def set_editable_table_name(self, name: str):
        self.editable_table_name = name
        return self

    def get_selected_samples(self) -> List[str]:
        return self.selected_samples

    def set_selected_samples(self, samples: List[str]):
        self.selected_samples = samples
        return self

    def get_selected_genes(self) -> List[str]:
        return self.selected_genes

    def set_selected_genes(self, genes: List[str]):
        self.selected_genes = genes
        return self

    def get_fields(self) -> List[tuple[str, bool]]:
        return self.fields

    def set_fields(self, fields: List[tuple[str, bool]]):
        self.fields = fields
        return self

    def get_query_definition(self) -> dict:
        """Get the query definition."""
        return self.query_definition

    # Should be called whenever the query template is updated
    def compute_fields(self):
        q = self.select_query()
        try:
            new_fields = {
                c: True
                for c in self.datalake.run_with_connection(
                    "validation", lambda conn: conn.sql(q).columns
                )
            }
            for f_name, checked in self.fields:
                if f_name in new_fields:
                    new_fields[f_name] = checked
            self.fields = [(f_name, checked) for f_name, checked in new_fields.items()]
        except Exception as e:
            LOGGER.error(f"Error computing fields: {e}\nQuery: {q}")
        return self

    def setup_query_template(self, definition: dict):
        """Set up the query template from a definition."""
        self.query_definition = definition
        self.query_template = build_query_template(definition)
        return self

    def setup_query(
        self,
        query_definition: dict,  # Mandatory: the select query definition
        editable_table_name: str,  # Mandatory: the name of the editable table
        readonly_files: List[str],  # Mandatory: the list of readonly files
        **kwargs,  # Optional: additional parameters.
    ) -> "QueryComponent":
        """Builds a query template from a json object.
        Provided json object must have a select key at the root level.

        Args:
            query_definition (dict): The query definition
            editable_table_name (str): The name of the editable table
            readonly_files (List[str]): The list of readonly files
            **kwargs: Additional parameters. Currently supports:
                - selected_genes (List[str]): List of selected genes (when used with validation component)
                - selected_samples (List[str]): List of selected samples (when used with validation component)
        """
        self.setup_query_template(query_definition)

        self.set_editable_table_name(editable_table_name)
        self.set_readonly_table(readonly_files)
        if "selected_genes" in kwargs:
            self.set_selected_genes(kwargs["selected_genes"])
        if "selected_samples" in kwargs:
            self.set_selected_samples(kwargs["selected_samples"])

        self.compute_fields()

        return self

    def select_query(self, paginated=True, columns=None, where=None) -> str:
        """Generates the select query_names to run on the database. Set paginated to False if you need a query that returns all rows (i.e. for counting)."""
        if not self.readonly_table:
            return ""

        # No columns provided, use all fields or selected fields
        if not columns:
            if self.fields:
                columns = ",".join([f'"{f}"' for f, c in self.fields if c])
            else:
                columns = "*"

        fields = columns

        order_by = (
            " ORDER BY " + ", ".join([f'"{ob[0]}" {ob[1]}' for ob in self.order_by])
            if self.order_by
            else ""
        )

        pagination = f" LIMIT {self.limit} OFFSET {self.offset}" if paginated else ""

        additional_where = where or (
            f" WHERE {self.filter_tree_to_string(self.applied_filter)}"
            if self.applied_filter and self.filter_tree_to_string(self.applied_filter)
            else ""
        )

        return f"SELECT {fields} FROM ({self.query_template}){additional_where}{order_by}{pagination}".format(
            **{
                "main_table": self.readonly_table,
                "user_table": f'"{self.editable_table_name}"',
                "pwd": self.datalake.datalake_path,
                "selected_genes": duck_db_literal_string_tuple(self.selected_genes),
                "selected_samples": duck_db_literal_string_tuple(self.selected_samples),
                **self.variables,
            }
        )

    def set_filter(self, filter_tree: dict):
        """Add a filter to the query. The filter_tree is a dict that can be converted to a FilterItem."""
        if not isinstance(filter_tree, dict):
            raise ValueError("Filter tree must be a dict")
        try:
            flt.FilterItem.from_json(filter_tree)
        except ValueError as e:
            raise ValueError(f"Invalid filter tree: {e}")
        self.applied_filter = filter_tree
        return self

    def get_filter(self) -> dict:
        """Get the filter tree of the query."""
        return self.applied_filter

    def get_order_by(self) -> List[list[str, str]]:
        """Get the order by expression of the query."""
        return self.order_by

    def set_order_by(self, order_by: List[list[str, str]]):
        """Set the order by expression of the query."""
        if not isinstance(order_by, list):
            raise ValueError("Order by must be a list of [field, order] pairs")
        for ob in order_by:
            if not isinstance(ob, list) or len(ob) != 2:
                raise ValueError("Each order by item must be a list of [field, order]")
        self.order_by = order_by
        return self

    def add_order_by(self, colname: str, order: str):
        if not self.order_by:
            self.order_by = []
        self.order_by.append([colname, order])
        return self

    def get_variant_info(self, validation_hash: int, columns: List[str] = None):

        variant_info = self.datalake.run_with_connection(
            "validation",
            lambda conn: conn.sql(
                self.select_query(
                    paginated=True,
                    columns=",".join([f'"{f}"' for f in columns]) if columns else "*",
                    where=f'WHERE ".validation_hash" = {validation_hash}',
                )
            )
            .pl()
            .to_dicts(),
        )
        variant_info = variant_info[0] if variant_info else {}
        return variant_info

    def count_query(self):
        return (
            f"SELECT COUNT(*) AS count_star FROM ({self.select_query(paginated=False)})"
        )

    def is_valid(self):
        return bool(self.readonly_table) and self.datalake

    def get_table_data(self) -> List[dict]:
        q = self.select_query()
        return self.datalake.run_with_connection(
            "validation", lambda conn: run_sql(q, conn)
        )

    def get_row_count(self) -> int:
        q = self.count_query()
        return self.datalake.run_with_connection(
            "validation", lambda conn: run_sql(q, conn)[0]["count_star"]
        )

    def commit(self):
        # Empty data before updating
        self.header = []
        self.data = []
        self.row_count = 0
        self.page_count = 1

        # Query is not valid, do nothing. Previous lines are for cleanup
        if not self.is_valid():
            # Now we can emit the signal: invalid query means no data
            self.query_changed.emit()
            return

        dict_data = self.get_table_data()
        # We have data, let's save it
        if dict_data:
            self.header = list(dict_data[0].keys())
            self.data = [list(row.values()) for row in dict_data]
        # There is no data, we can return early
        else:
            self.query_changed.emit()
            return

        self.row_count = self.get_row_count()
        self.page_count = max(
            self.row_count // self.limit, ceil(self.row_count / self.limit)
        )
        if self.current_page > self.page_count:
            self.offset = 0
        self.query_changed.emit()

    def widget(self):
        return self.view

    def filter_tree_to_string(self, f: dict) -> str:
        return str(flt.FilterItem.from_json(f))

    def close_component(self):
        LOGGER.debug(
            f"Starting close_component for {self.instance_name} (AKA {self.ui_name})"
        )
        super().close_component()
        self.deleteLater()

    def to_json(self) -> dict:
        """Convert the query component to a JSON-like dict."""
        return {
            "query_definition": self.query_definition,
            "readonly_files": self.readonly_files,
            "editable_table_name": self.editable_table_name,
            "selected_genes": self.selected_genes,
            "selected_samples": self.selected_samples,
            "fields": self.fields,
            "applied_filter": self.applied_filter,
            "order_by": self.order_by,
            "variables": self.variables,
            "ui_name": self.ui_name,
            "instance_name": self.instance_name,
        }

    def from_json(self, data: dict):
        """Load the query component from a JSON-like dict."""
        self.setup_query(**data)
        self.set_fields(data["fields"])
        self.set_filter(data["applied_filter"])
        self.set_order_by(data["order_by"])
        self.variables = data.get("variables", {})
        self.ui_name = data.get("ui_name", self.app.translate("Unnamed query"))
        self.view.setWindowTitle(self.ui_name)
        return self

    def __del__(self):
        LOGGER.info(f"QueryComponent {self.instance_name} (AKA {self.ui_name}) deleted")


if __name__ == "__main__":

    from commons import yaml_load

    data = yaml_load("config_folder/validation_methods/validation_ppi.yaml")
    q = build_query_template(data[0]["query"])
    print(q)
