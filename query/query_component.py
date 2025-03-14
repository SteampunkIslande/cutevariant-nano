#!/usr/bin/env python

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


class QueryComponent(ap.AppComponent):

    RESERVED_VARIABLES = [
        "main_table",
        "user_table",
        "pwd",
        "selected_genes",
        "selected_samples",
    ]

    # Signal for external use (tell the UI to update)
    query_changed = qc.Signal()

    # Signal for internal use only
    query_setup_changed = qc.Signal()

    def __init__(
        self, app: ap.App, instance_name: str, parent_component: ap.AppComponent
    ):
        super().__init__(app, instance_name, parent_component)

        # Safer to init state before setting up the view
        self.init_state()

        self.view = query.query_table_widget.QueryTableWidget(self.app, self)
        self.view.setWindowTitle(self.instance_name.split("/")[-1])

    def get_datalake(self) -> "dl.Datalake":
        return self.app.get_component("datalake")

    def init_state(self):
        # When we create a new Query, we want to reset everything, except for the datalake path...
        self.query_template = ""
        self.query_definition: dict = None

        # Order by, updated by the order_by_changed signal
        self.order_by = None

        # All fields available to the user. Including those starting with a dot (hidden by default in the UI).
        # Also includes fields that are not selected in the view. So that they can be filtered on.
        self.all_fields = []

        # Filter tree, updated by the filters_changed signal
        self.applied_filter = {}

        # Essential members, not meant to change
        self.readonly_table = None
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

        return self

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

    def get_limit(self) -> int:
        return self.limit

    def set_limit(self, limit: int):
        self.limit = limit
        return self

    def get_offset(self) -> int:
        return self.offset

    def set_offset(self, offset: int):
        self.offset = offset
        return self

    def get_page(self) -> int:
        return self.current_page

    def set_page(self, page: int):
        self.current_page = page
        self.set_offset((page - 1) * self.limit)
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

    def get_data(self):
        return self.data

    def get_header(self):
        return self.header

    def get_readonly_table(self) -> str:
        return self.readonly_table

    def set_readonly_table(self, files: List[str]):
        if not files:
            return self
        datalake = self.get_datalake()
        if not datalake:
            return self

        self.readonly_table = f"read_parquet({duck_db_literal_string_list(datalake.relative_to_absolute(f) for f in files)})"
        return self

    def get_editable_table_human_readable_name(self) -> str:
        datalake = self.get_datalake()
        if not datalake or not datalake.datalake_path:
            return self.app.translate("No datalake selected")

        return datalake.run_with_connection(
            "validation",
            lambda conn: conn.sql(
                f"SELECT table_name FROM validations WHERE table_uuid = '{self.editable_table_name}'"
            ).fetchone()[0],
        ) or self.app.translate(
            "No table with name {}".format(self.editable_table_name)
        )

    def get_column_info(self, colname: str):
        select = self.select_query(paginated=False, columns=f'"{colname}"')
        datalake = self.get_datalake()
        if not datalake:
            return
        (datatype, nullable) = datalake.run_with_connection(
            "validation",
            lambda conn: conn.sql(
                f"SELECT column_type,null FROM (describe({select}))"
            ).fetchone(),
        )
        top_10_values = datalake.run_with_connection(
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

    def set_selected_samples(self, samples: List[str]):
        self.selected_samples = samples
        return self

    def get_selected_samples(self) -> List[str]:
        return self.selected_samples

    def set_selected_genes(self, genes: List[str]):
        self.selected_genes = genes
        return self

    def get_selected_genes(self) -> List[str]:
        return self.selected_genes

    def setup_query(self, data: dict) -> "QueryComponent":
        """Builds a query template from a json object.
        Provided json object must have a select key at the root level.

        Args:
            data (dict): The json object to build the query template from
        """
        self.query_definition = data
        self.query_template = build_query_template(data)
        self.query_setup_changed.emit()
        self.all_fields = data["select"]["fields"]

        self.broadcast.emit(
            "query_fields_changed",
            "query",
            self.instance_name,
            {"fields": self.list_exposed_fields()},
        )

        return self

    def select_query(self, paginated=True, columns=None, where=None) -> str:
        """Generates the select query_names to run on the database. Set paginated to False if you need a query that returns all rows (i.e. for counting)."""
        if not self.readonly_table:
            return ""

        fields = columns or "*"

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
                "pwd": self.get_datalake().datalake_path,
                "selected_genes": duck_db_literal_string_tuple(self.selected_genes),
                "selected_samples": duck_db_literal_string_tuple(self.selected_samples),
                **self.variables,
            }
        )

    def get_all_fields(self):
        return self.all_fields

    def list_exposed_fields(self):
        q = self.select_query(paginated=True, columns="COLUMNS('^[^.].+$')")
        if not q:
            return []

        cols = self.get_datalake().run_with_connection(
            "validation",
            lambda conn: conn.sql(q).columns,
        )
        return cols

    def get_variant_info(self, validation_hash: int, columns: List[str] = None):

        variant_info = self.get_datalake().run_with_connection(
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
        return bool(self.readonly_table) and self.get_datalake()

    def to_do(self):
        if not self.get_datalake().datalake_path:
            return "Please select a datalake"
        if not self.readonly_table:
            return "Please select a main table"
        if not self.editable_table_name:
            return "Please select a validation table"

    def get_table_data(self) -> List[dict]:
        q = self.select_query()
        return self.get_datalake().run_with_connection(
            "validation", lambda conn: run_sql(q, conn)
        )

    def get_row_count(self) -> int:
        q = self.count_query()
        return self.get_datalake().run_with_connection(
            "validation", lambda conn: run_sql(q, conn)[0]["count_star"]
        )

    def update_data(self):
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

    def commit(self):
        self.query_setup_changed.emit()
        self.update_data()

    def get_variant_info_component(self) -> ap.AppComponent:
        return

    def widget(self):
        return self.view

    def save_to_session(self):
        return {}

    def load_from_session(self, session: dict):
        return

    def get_menubar_entries(self):
        return []

    def get_contextmenu_entries(self, local_info: dict):
        return []

    def on_start(self):
        return

    def get_instance_name(self) -> str:
        return self.instance_name

    def filter_tree_to_string(self, f: dict) -> str:
        return str(flt.FilterItem.from_json(f))

    def generic_receiver(
        self, action, sender_component_name, sender_instance_name, payload
    ):
        if action == "order_by_changed":
            if sender_instance_name == f"{self.instance_name}/order_by":
                self.order_by = payload["order_by_expression"]
                self.commit()
        if action == "filters_changed":
            if sender_instance_name == f"{self.instance_name}/filters":
                self.applied_filter = payload["filter_tree"]
                self.commit()
        if action == "selected_fields_changed":
            if sender_instance_name == f"{self.instance_name}/fields":
                self.view.update_selected_fields(payload["fields"])
                self.commit()


def register_component():
    return "query", {
        "instantiation_policy": "multi",
        "instantiate_on": "demand",
        "class": QueryComponent,
    }


if __name__ == "__main__":

    from commons import yaml_load

    data = yaml_load("config_folder/validation_methods/validation_ppi.yaml")
    q = build_query_template(data[0]["query"])
    print(q)
