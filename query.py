#!/usr/bin/env python

import os
from pathlib import Path
import pickle
from typing import Any, List, Tuple, Union

import duckdb as db
import PySide6.QtCore as qc
from cachetools import cached

from enum import Enum

from commons import duck_db_literal_string_list


@cached(cache={})
def run_sql(query: str, conn: db.DuckDBPyConnection = None) -> Union[List[dict], None]:
    if not conn:
        return None
    res = conn.sql(query)
    if res:
        return res.pl().to_dicts()


class FilterType(Enum):
    AND = "AND"
    OR = "OR"
    LEAF = "LEAF"


class Table:
    def __init__(self, name: str, alias: str) -> None:
        self.name = name
        self.alias = alias

    def get_alias(self) -> str:
        return self.alias or self.name

    def __str__(self) -> str:
        if self.alias:
            return f"{self.name} {self.alias}"
        return self.name


class Field:
    def __init__(
        self, name: str, table: Table = None, alias: str = None, is_expression=False
    ):
        self.name = name
        self.table = table
        self.alias = alias
        self.is_expression = is_expression

    def __format__(self, format_spec: str) -> str:
        if format_spec == "q":
            if self.table:
                base = f'"{self.table.get_alias()}"."{self.name}"'
                if self.is_expression:
                    base = base.format(table=self.table.get_alias())
            else:
                base = f'"{self.name}"'

            if self.alias:
                base = f"{base} AS {self.alias}"

            return base
        else:
            if self.table:
                base = f"{self.table.get_alias()}.{self.name}"
                if self.is_expression:
                    base = base.format(table=self.table.get_alias())
            else:
                base = f"{self.name}"
            if self.alias:
                base = f"{base} AS {self.alias}"
            return base

    def __str__(self) -> str:
        return self.__format__("")


class Join:
    def __init__(
        self,
        table: Table,
        left_on: Field,
        right_on: Field,
        join_type: str = "JOIN",
    ):
        self.table = table
        self.left_on = left_on
        self.right_on = right_on
        self.join_type = join_type

    def __str__(self):
        return f"{self.join_type} {self.table} ON {self.left_on:q} = {self.right_on:q}"


class FilterExpression:
    def __init__(
        self,
        filter_type=FilterType.LEAF,
        expression: str = None,
        parent: "FilterExpression" = None,
    ) -> None:
        self.filter_type = filter_type
        self.expression = expression
        self.children: List["FilterExpression"] = []
        self.parent = parent
        if self.parent:
            self.parent.children.append(self)

    def add_child(self, child: "FilterExpression"):
        self.children.append(child)
        child.parent = self

    def __bool__(self) -> bool:
        if self.filter_type == FilterType.LEAF:
            return bool(self.expression)
        else:
            return bool(self.children)

    def __str__(self) -> str:
        if self.filter_type == FilterType.LEAF:
            return self.expression
        else:
            if self.parent:
                return str(self.filter_type).join(
                    f"({str(child)})" for child in self.children
                )
            else:
                return str(self.filter_type).join(str(child) for child in self.children)


class Select:
    def __init__(
        self,
        fields: List[Field],
        main_table: Table,
        additional_tables: List[Join] = None,
        filters: FilterExpression = None,
        order_by: List[Tuple[Field, str]] = None,
        limit: int = 10,
        offset: int = 0,
    ):
        self.fields = fields
        self.main_table = main_table
        self.joins = additional_tables
        self.filter = filters
        self.order_by = order_by
        self.limit = limit
        self.offset = offset

    def __format__(self, format_spec: str) -> str:
        filt = ""
        if self.filter:
            filt = f" WHERE {self.filter}"

        order = ""
        if self.order_by:
            order = f" ORDER BY {', '.join(map(lambda f:f'{f[0]:q} {f[1]}', self.order_by))}"

        joins = ""
        if self.joins:
            joins = " ".join(map(str, self.joins))

        q = f"SELECT {', '.join(map(lambda f:f'{f:q}', self.fields))} FROM {self.main_table} {joins}{filt}{order} LIMIT {self.limit} OFFSET {self.offset}"

        if format_spec == "p":
            q = f"({q})"
        return q

    def __str__(self):
        return self.__format__("")

    def save(self, filename: Path):
        with open(filename, "w") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(filename: Path):
        with open(filename, "r") as f:
            return pickle.load(f)


class Query(qc.QObject):
    # Signals for internal use only
    fields_changed = qc.Signal()
    filters_changed = qc.Signal()
    order_by_changed = qc.Signal()
    limit_changed = qc.Signal()
    offset_changed = qc.Signal()
    from_changed = qc.Signal()

    # Signals for external use
    query_changed = qc.Signal()

    datalake_changed = qc.Signal()

    def __init__(self, conn: db.DuckDBPyConnection = None) -> None:
        super().__init__()

        self.init_state()

        self.fields_changed.connect(self.update)
        self.filters_changed.connect(self.update)
        self.order_by_changed.connect(self.update)
        self.limit_changed.connect(self.update)
        self.offset_changed.connect(self.update)
        self.from_changed.connect(self.update)

        self.datalake_path = None

        self.conn = conn

    def init_state(self):
        self.datalake_path = None
        self.fields = []
        self.main_table = None
        self.additional_tables = dict()
        self.filter = FilterExpression()
        self.order_by = []
        self.limit = 10
        self.offset = 0

        self.current_page = 1
        self.page_count = 1

        self.data = []
        self.header = []

    def add_field(self, field: Union[str, Field]):
        if isinstance(field, str):
            field = Field(field, None)
        self.fields_changed.emit()

        return self

    def get_fields(self) -> List[Field]:
        return self.fields

    def set_fields(self, fields: List[Field]):
        self.fields = fields
        self.fields_changed.emit()

        return self

    def get_filter(self) -> FilterExpression:
        return self.filter

    def set_filter(self, filter: FilterExpression):
        self.filter = filter
        self.filters_changed.emit()

        return self

    def add_filter(self, new_filter: FilterExpression, parent: FilterExpression = None):
        if parent:
            parent.add_child(new_filter)
        else:
            self.filter.add_child(new_filter)
        self.filters_changed.emit()

        return self

    def get_order_by(self) -> List[List[Union[Field, str]]]:
        return self.order_by

    def set_order_by(self, order_by: List[List[Union[Field, str]]]):
        self.order_by = order_by
        self.order_by_changed.emit()

        return self

    def get_limit(self) -> int:
        return self.limit

    def set_limit(self, limit: int):
        self.limit = limit
        self.limit_changed.emit()

        return self

    def get_offset(self) -> int:
        return self.offset

    def set_offset(self, offset: int):
        self.offset = offset
        self.offset_changed.emit()
        return self

    def set_page(self, page: int):
        self.current_page = page
        self.set_offset((page - 1) * self.limit)

        return self

    def get_page(self) -> int:
        return self.current_page

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

    def mute(self):
        self.blockSignals(True)
        return self

    def unmute(self):
        self.blockSignals(False)
        return self

    def set_main_files(self, files: List[Path]):
        self.main_table = Table(
            f"read_parquet({duck_db_literal_string_list(files)})", "main_table"
        )
        self.from_changed.emit()
        return self

    def add_table(
        self,
        name: str,
        table: Table,
        left_on: Field,
        right_on: Field,
        join_type: str = "JOIN",
    ):
        self.additional_tables[name] = Join(table, left_on, right_on, join_type)
        self.from_changed.emit()
        return self

    def select_query(self):
        if not self.main_table:
            return ""

        q = Select(
            fields=self.fields,
            main_table=self.main_table,
            additional_tables=list(self.additional_tables.values()),
            filters=self.filter,
            order_by=self.order_by,
            limit=self.limit,
            offset=self.offset,
        )
        return str(q)

    def count_query(self):
        field = Field("COUNT(*) AS count_star", is_expression=True)

        q = Select(
            fields=[field],
            main_table=self.main_table,
            additional_tables=list(self.additional_tables.values()),
            filters=self.filter,
        )
        return str(q)

    def is_valid(self):
        return bool(self.main_table) and bool(self.fields) and self.datalake_path

    def to_do(self):
        if not self.datalake_path:
            return "Please select a datalake path"
        if not self.main_table:
            return "Please select a main table"
        if not self.fields:
            return "Please select some fields"

    def update(self):
        self.blockSignals(True)
        self.header = []
        self.data = []
        self.row_count = 0
        self.page_count = 1
        # Query is not valid, do nothing. Previous lines are for cleanup
        if not self.is_valid():
            self.blockSignals(False)
            # Now we can emit the signal: invalid query means no data
            self.query_changed.emit()
            return
        # Running the query might throw an exception, we catch it and print it
        try:
            dict_data = run_sql(self.select_query(), self.conn)
        except db.ParserException as e:
            print(e)
            self.blockSignals(False)
            self.query_changed.emit()
            # Return early, dict_data is not set
            return

        # We have data, let's save it
        if dict_data:
            self.header = list(dict_data[0].keys())
            self.data = [list(row.values()) for row in dict_data]
        # There is no data, we can return early (after resetting the page count and row count)
        else:
            self.row_count = 0
            self.page_count = 1
            self.set_page(1)
            self.blockSignals(False)
            self.query_changed.emit()
            return
        self.row_count = run_sql(self.count_query(), self.conn)[0]["count_star"]
        self.page_count = self.row_count // self.limit
        if self.row_count % self.limit > 0:
            self.page_count = self.page_count + 1
        if self.current_page > self.page_count:
            self.set_page(self.page_count)
            self.update()  # TODO: Fix edge case
        self.blockSignals(False)
        self.query_changed.emit()

    def set_datalake_path(self, path: str):
        self.datalake_path = path
        # TODO: iterate over a dictionary of all possibly opened databases...
        self.conn = db.connect(os.path.join(path, "validation.db"))
        self.datalake_changed.emit()
        return self

    def save(self, filename: Path):
        with open(filename, "wb") as f:
            pickle.dump(
                {
                    "fields": self.fields,
                    "main_table": self.main_table,
                    "additional_tables": self.additional_tables,
                    "filter": self.filter,
                    "order_by": self.order_by,
                    "limit": self.limit,
                    "offset": self.offset,
                },
                f,
            )

    @staticmethod
    def load(filename: Path) -> "Query":
        with open(filename, "rb") as f:
            self_dic = pickle.load(f)
            q = Query()
            q.fields = self_dic["fields"]
            q.main_table = self_dic["main_table"]
            q.additional_tables = self_dic["additional_tables"]
            q.filter = self_dic["filter"]
            q.order_by = self_dic["order_by"]
            q.limit = self_dic["limit"]
            q.offset = self_dic["offset"]
            return q


if __name__ == "__main__":
    pass
