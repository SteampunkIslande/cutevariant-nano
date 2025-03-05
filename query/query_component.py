#!/usr/bin/env python

from math import ceil
from typing import List, Union

import duckdb as db
import PySide6.QtCore as qc

import app as ap
import datalake.datalake_component as dl
import fields.fields_component as fld_cmp
import fields.fields_model as fldm
import filters.filters as flt
import filters.filters_component as flt_cmp
import filters.filters_model as fltm
import order_by.order_by_model as obm
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

    query_setup_changed = qc.Signal()

    def __init__(
        self, app: ap.App, instance_name: str, parent_component: ap.AppComponent
    ):
        super().__init__(app, instance_name, parent_component)
        self.app = app
        self.instance_name = instance_name
        self.datalake: dl.Datalake = self.app.get_component("datalake")

        self.init_state()

        self.fields_model = fldm.FieldsModel(self)
        self.fields_model.load()
        self.fields_model.model_changed.connect(self.update_data)

        self.filter_model = fltm.FilterModel(self)
        self.filter_model.load(
            {
                "filter_type": "ROOT",
                "children": [{"filter_type": "AND", "children": []}],
            }
        )
        self.filter_model.model_changed.connect(self.update_data)

        self.order_by_model = obm.OrderByModel(self)
        self.order_by_model.load([])
        self.order_by_model.model_changed.connect(self.update_data)

        self.init_children_components()

    def init_state(self):
        # When we create a new Query, we want to reset everything, except for the datalake path...
        self.query_template = ""
        self.query_definition: dict = None
        self.order_by = None

        self.readonly_table = None
        self.editable_table_name = None
        self.selected_samples = []
        self.selected_genes = []

        self.limit = 10
        self.offset = 0

        self.current_page = 1
        self.page_count = 1

        self.data = []
        self.header = []
        self.database_path = None

        self.variables = dict()

        return self

    def init_children_components(self):
        self.fields_component = self.app.instantiate_component(
            "fields", f"{self.instance_name}.fields", self
        )
        self.filters_component = self.app.instantiate_component(
            "filters", f"{self.instance_name}.filters", self
        )

        self.view = query.query_table_widget.QueryTableWidget(self.app, self)

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

    def set_order_by(self, order_by: list[tuple[str, str]]):
        self.order_by_model.load(order_by)
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
        self.readonly_table = f"read_parquet({duck_db_literal_string_list(self.datalake.relative_to_absolute(f) for f in files)})"
        self.query_changed.emit()
        return self

    def get_editable_table_human_readable_name(self) -> str:
        if not self.datalake.datalake_path:
            return self.app.translate("Pas de datalake sélectionné")
        conn = self.datalake.get_database("validation")
        try:
            name = conn.sql(
                f"SELECT validation_name FROM validations WHERE table_uuid = '{self.editable_table_name}'"
            ).fetchall()[0][0]
        except IndexError:
            name = self.app.translate("Table de validation introuvable")
        finally:
            conn.close()
        return name

    def get_column_info(self, colname: str):
        select = self.select_query(paginated=False, columns=f'"{colname}"')
        conn = self.datalake.get_database("validation")
        (datatype, nullable) = conn.sql(
            f"SELECT column_type,null FROM (describe({select}))"
        ).fetchone()
        top_10_values = [
            c[1]
            for c in conn.sql(
                f"""SELECT COUNT(*) AS count,"{colname}" FROM ({select}) GROUP BY "{colname}" ORDER BY count DESC LIMIT 10"""
            ).fetchall()
        ]

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

    def get_selected_fields(self) -> List[str]:
        return self.fields_model.checked_fields()

    def setup_query(self, data: dict) -> "QueryComponent":
        """Builds a query template from a json object.
        Provided json object must have a select key at the root level.

        Args:
            data (dict): The json object to build the query template from
        """
        self.query_definition = data
        self.query_template = build_query_template(data)
        self.query_setup_changed.emit()
        return self

    def select_query(self, paginated=True, columns=None, where=None) -> str:
        """Generates the select query to run on the database. Set paginated to False if you need a query that returns all rows (i.e. for counting)."""
        if not self.readonly_table:
            return ""

        fields = columns or "*"
        order_by_data = self.order_by_model.get_data()

        order_by = (
            " ORDER BY " + ", ".join([f'"{ob[0]}" {ob[1]}' for ob in order_by_data])
            if order_by_data
            else ""
        )

        pagination = f" LIMIT {self.limit} OFFSET {self.offset}" if paginated else ""

        additional_where = where or (
            f" WHERE {str(self.filter_model)}" if str(self.filter_model) else ""
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

    def list_exposed_fields(self):

        if not self.query_template:
            return []
        print(self.query_template)

        cols = self.datalake.run_with_connection(
            "validation",
            lambda conn: conn.sql(
                self.select_query(paginated=True, columns="COLUMNS('^[^.].+$')")
            ).columns,
        )
        return cols

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

    def to_do(self):
        if not self.datalake.datalake_path:
            return "Please select a datalake"
        if not self.readonly_table:
            return "Please select a main table"
        if not self.editable_table_name:
            return "Please select a validation table"

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
        self.update_data()

    def get_fields_component(self) -> fld_cmp.FieldsComponent:
        return self.fields_component

    def get_filters_component(self) -> flt_cmp.FiltersComponent:
        return self.filters_component

    def get_variant_info_component(self) -> ap.AppComponent:
        return

    def widget(self):
        return self.view


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
