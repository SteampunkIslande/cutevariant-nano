#!/usr/bin/env python

from math import ceil
from typing import List, Union

import duckdb as db
import PySide6.QtCore as qc

import datalake as dl
import filters_model as fm
from commons import duck_db_literal_string_list, duck_db_literal_string_tuple
from filters import FilterItem


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
            on = str(FilterItem.from_json(on))
        result += f" {how} JOIN {table} ON {on} "

    if "filter" in select_def:
        filter_def = select_def["filter"]
        filter_str = str(FilterItem.from_json(filter_def))
        result += f" WHERE {filter_str} "

    if "group_by" in select_def:
        group_by = select_def["group_by"]
        if isinstance(group_by, list):
            group_by = ",".join(group_by)
        result += f" GROUP BY {group_by} "

    if "order_by" in select_def:
        order_by = select_def["order_by"]

        result += " ORDER BY " + ", ".join(
            [f"{ob['field']} {ob['order']} " for ob in order_by]
        )

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


class Query(qc.QObject):

    RESERVED_VARIABLES = [
        "main_table",
        "user_table",
        "pwd",
        "selected_genes",
        "selected_samples",
    ]

    # Signal for external use (tell the UI to update)
    query_changed = qc.Signal()

    # Signal for internal use (tell the model to update)
    internal_changed = qc.Signal()

    def __init__(self, datalake: "dl.DataLake", parent=None):
        super().__init__(parent)
        self.datalake = datalake
        self.init_state()

        self.filter_model = fm.FilterModel()
        self.filter_model.load(
            {
                "filter_type": "ROOT",
                "children": [{"filter_type": "AND", "children": []}],
            }
        )
        self.filter_model.model_changed.connect(self.update_data)

        self.internal_changed.connect(self.update_data)

    def init_state(self):
        # When we create a new Query, we want to reset everything, except for the datalake path...
        self.query_template = None
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

        self.internal_changed.emit()

        return self

    def add_variable(self, key: str, value: str):
        if key in Query.RESERVED_VARIABLES:
            raise ValueError(f"Variable name {key} is reserved")
        self.variables[key] = value
        self.internal_changed.emit()
        return self

    def get_variable(self, key: str) -> str:
        return self.variables.get(key)

    def list_variables(self) -> List[str]:
        return list(self.variables.keys())

    def get_limit(self) -> int:
        return self.limit

    def set_limit(self, limit: int):
        self.limit = limit
        self.internal_changed.emit()
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
        self.internal_changed.emit()
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
            return qc.QCoreApplication.tr("Pas de datalake sélectionné")
        conn = self.datalake.get_database("validation")
        try:
            name = (
                conn.sql(
                    f"SELECT validation_name FROM validations WHERE table_uuid = '{self.editable_table_name}'"
                )
                .pl()
                .to_dicts()[0]["validation_name"]
            )
        except IndexError:
            name = qc.QCoreApplication.tr("Table de validation introuvable")
        finally:
            conn.close()
        return name

    def get_editable_table_name(self) -> str:
        return self.editable_table_name

    def set_editable_table_name(self, name: str):
        self.editable_table_name = name
        self.internal_changed.emit()
        return self

    def set_selected_samples(self, samples: List[str]):
        self.selected_samples = samples
        self.internal_changed.emit()
        return self

    def get_selected_samples(self) -> List[str]:
        return self.selected_samples

    def set_selected_genes(self, genes: List[str]):
        self.selected_genes = genes
        self.internal_changed.emit()
        return self

    def get_selected_genes(self) -> List[str]:
        return self.selected_genes

    def generate_query_template_from_json(self, data: dict) -> "Query":
        """Builds a query template from a json object.
        Provided json object must have a select key at the root level.

        Args:
            data (dict): The json object to build the query template from
        """
        self.query_template = build_query_template(data)
        self.internal_changed.emit()
        return self

    def select_query(self, paginated=True):
        """Generates the select query to run on the database. Set paginated to False if you need a query that returns all rows."""
        if not self.readonly_table:
            return ""

        pagination = f" LIMIT {self.limit} OFFSET {self.offset}" if paginated else ""

        additional_where = (
            f" WHERE {str(self.filter_model)}"
            if not self.filter_model.is_empty()
            else ""
        )

        return f"SELECT * FROM ({self.query_template}){additional_where}{pagination}".format(
            **{
                "main_table": self.readonly_table,
                "user_table": f'"{self.editable_table_name}"',
                "pwd": self.datalake.datalake_path,
                "selected_genes": duck_db_literal_string_tuple(self.selected_genes),
                "selected_samples": duck_db_literal_string_tuple(self.selected_samples),
                **{k: v for k, v in self.variables.items()},
            }
        )

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

        # Running the query might throw an exception, we catch it and print it
        conn = self.datalake.get_database("validation")

        try:
            dict_data = run_sql(self.select_query(), conn)
        except db.Error as e:
            print(e)
            print(self.select_query())
            conn.close()
            self.query_changed.emit()
            # Return early, dict_data is not set
            return

        # We have data, let's save it
        if dict_data:
            self.header = list(dict_data[0].keys())
            self.data = [list(row.values()) for row in dict_data]
        # There is no data, we can return early
        else:
            self.query_changed.emit()
            conn.close()
            return
        self.row_count = run_sql(self.count_query(), conn)[0]["count_star"]
        conn.close()
        self.page_count = max(
            self.row_count // self.limit, ceil(self.row_count / self.limit)
        )
        if self.current_page > self.page_count:
            self.offset = 0
        self.query_changed.emit()

    def mute(self):
        self.blockSignals(True)
        return self

    def unmute(self):
        self.blockSignals(False)
        return self

    def to_json(self):
        return {
            "query_template": self.query_template,
            "order_by": self.order_by,
            "readonly_table": self.readonly_table,
            "editable_table_name": self.editable_table_name,
            "limit": self.limit,
            "offset": self.offset,
            "current_page": self.current_page,
            "page_count": self.page_count,
            "data": self.data,
            "header": self.header,
            "variables": self.variables,
        }

    @staticmethod
    def from_json(data: dict, datalake: "dl.DataLake") -> "Query":
        query = Query(datalake)
        query.query_template = data["query_template"]
        query.order_by = data["order_by"]
        query.readonly_table = data["readonly_table"]
        query.editable_table_name = data["editable_table_name"]
        query.limit = data["limit"]
        query.offset = data["offset"]
        query.current_page = data["current_page"]
        query.page_count = data["page_count"]
        query.data = data["data"]
        query.header = data["header"]
        query.variables = data["variables"]
        return query


if __name__ == "__main__":

    from commons import yaml_load

    data = yaml_load("config_folder/validation_methods/validation_ppi.yaml")
    q = build_query_template(data[0]["query"])
    print(q)
