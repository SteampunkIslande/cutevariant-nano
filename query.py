#!/usr/bin/env python

import os
import pickle
import sys
from math import ceil
from pathlib import Path
from typing import List, Union

import duckdb as db
import PySide6.QtCore as qc

from commons import duck_db_literal_string_list
from filters import FilterExpression, FilterType


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

    RESERVED_VARIABLES = ["main_table", "user_table"]

    # Signals for external use
    query_changed = qc.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_state()

    def init_state(self):
        # When we create a new Query, we want to reset everything, except for the datalake path...
        self.query_template = None
        self.order_by = None
        self.readonly_table = None
        self.root_filter = FilterExpression(FilterType.AND)
        self.editable_table_name = None

        self.limit = 10
        self.offset = 0

        self.current_page = 1
        self.page_count = 1

        self.data = []
        self.header = []

        self.editable_table_name = None
        self.database_path = None

        self.variables = dict()

    def add_variable(self, key: str, value: str):
        if key in Query.RESERVED_VARIABLES:
            raise ValueError(f"Variable name {key} is reserved")
        self.variables[key] = value
        return self

    def get_variable(self, key: str) -> str:
        return self.variables.get(key)

    def list_variables(self) -> List[str]:
        return list(self.variables.keys())

    def add_filter(self, new_filter: FilterExpression, parent: FilterExpression = None):
        if parent:
            parent.add_child(new_filter)
        else:
            self.root_filter.add_child(new_filter)

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

    def set_readonly_table(self, files: List[Path]):
        if not files:
            return self
        self.readonly_table = duck_db_literal_string_list(files)
        return self

    def get_database_path(self) -> str:
        return self.database_path

    def set_database_path(self, path: str):
        self.database_path = path
        return self

    def get_editable_table_name(self) -> str:
        return self.editable_table_name

    def set_editable_table_name(self, name: str):
        self.editable_table_name = name
        return self

    def select_query(self):
        if not self.readonly_table:
            return ""

        return f"{self.query_template} WHERE {str(self.root_filter)} LIMIT {self.limit} OFFSET {self.offset} ORDER BY {self.order_by}".format(
            **{
                "main_table": self.readonly_table,
                "user_table": self.editable_table_name,
                **{k: v for k, v in self.variables.items()},
            }
        )

    def count_query(self):
        return f"SELECT COUNT(*) AS count_star FROM {self.query_template} WHERE {str(self.root_filter)}".format(
            **{
                "main_table": self.readonly_table,
                "user_table": self.editable_table_name,
                **{k: v for k, v in self.variables.items()},
            }
        )

    def is_valid(self):
        return bool(self.readonly_table) and self.datalake_path

    def to_do(self):
        if not self.datalake_path:
            return "Please select a datalake path"
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
        self.first_page()

        # Query is not valid, do nothing. Previous lines are for cleanup
        if not self.is_valid():
            # Now we can emit the signal: invalid query means no data
            self.query_changed.emit()
            return

        # Running the query might throw an exception, we catch it and print it
        conn = db.connect(self.database_path)
        try:
            dict_data = run_sql(self.select_query(), conn)
        except db.Error as e:
            print(e)
            print(self.select_query())
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
            return
        self.row_count = run_sql(self.count_query(), conn)[0]["count_star"]
        self.page_count = max(
            self.row_count // self.limit, ceil(self.row_count / self.limit)
        )
        if self.current_page > self.page_count:
            self.set_page(1)
            self.update_data()  # TODO: Fix edge case
        self.blockSignals(False)
        self.query_changed.emit()

    def set_datalake_path(self, path: str):
        if not os.path.isdir(path):
            return self
        os.chdir(path)
        self.datalake_path = path
        self.query_changed.emit()
        return self


class DataLake(qc.QObject):

    folder_changed = qc.Signal()

    instance_count = 0

    def __init__(self) -> None:
        super().__init__()

        DataLake.instance_count += 1
        # This is supposed to be a singleton. Dirty hack to enforce it
        if DataLake.instance_count > 1:
            print("Only one instance of DataLake is allowed")
            sys.exit(1)

        self.datalake_path = None
        self.queries = dict()

    def set_datalake_path(self, path: str):
        self.datalake_path = path
        self.folder_changed.emit()
        return self

    def add_query(self, name: str, query: Query):
        self.queries[name] = query

    def get_query(self, name: str) -> Query:
        return self.queries.get(name)

    def save(self, filename: Path):
        with open(filename, "wb") as f:
            pickle.dump(
                {
                    "datalake_path": self.datalake_path,
                    "queries": {k: v for k, v in self.queries.items()},
                },
                f,
            )

    @staticmethod
    def load(filename: Path) -> "DataLake":
        with open(filename, "rb") as f:
            self_dic = pickle.load(f)
            datalake = DataLake()
            datalake.set_datalake_path(self_dic["datalake_path"])
            queries: dict = self_dic["queries"]
            for name, query in queries.items():
                datalake.add_query(name, query)
            return datalake


if __name__ == "__main__":
    pass
