#!/usr/bin/env python

import os
import pickle
import sys
from enum import Enum
from pathlib import Path
from typing import List, Tuple, Union

import duckdb as db
import PySide6.QtCore as qc
from cachetools import cached

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
    def __init__(self, name: str, alias: str, quoted=False) -> None:
        self.name = name
        self.alias = alias
        self.quoted = quoted

    def get_alias(self) -> str:
        return self.alias or self.name

    def __format__(self, format_spec: str) -> str:

        # Use alias or name (a takes precedence over all other format specifiers)
        if "a" in format_spec:
            base = self.alias
        else:
            base = self.name

        if self.quoted:
            base = f'"{base}"'

        # Use in join clause
        if "j" in format_spec:
            base = f"{base} {self.alias}"

        # Use in select clause
        if "s" in format_spec:
            base = f"{base} {self.alias}"

        return base

    def __str__(self) -> str:
        return self.__format__("")


class Field:
    def __init__(
        self, name: str, table: Table = None, alias: str = None, is_expression=False
    ):
        self.name = name
        self.table = table
        self.alias = alias
        self.is_expression = is_expression

    def __format__(self, format_spec: str) -> str:
        # Format spec can be s if the field is in a select clause, j if it's in a join clause, and w if it's in a where clause

        if len(set("sjw").intersection(format_spec)) > 1:
            raise ValueError("Format specifiers s, j, and w are mutually exclusive")

        if self.is_expression:
            base = self.name.format(table=f"{self.table:a}" if self.table else "")
            if "a" in format_spec and self.alias:
                return f"{base} AS {self.alias}"

        if "s" in format_spec:
            base = self.name if "q" not in format_spec else f'"{self.name}"'
            if self.table:
                base = f"{self.table:qa}.{base}"
            if self.alias:
                base = f"{base} AS {self.alias}"

        elif "j" in format_spec:
            base = self.name if not self.alias else self.alias
            base = f'"{base}"' if "q" in format_spec else base
            if self.table:
                base = f"{self.table:qa}.{base}"

        elif "w" in format_spec:
            base = self.name if not self.alias else self.alias
            if self.is_expression:
                base = base.format(table=f"{self.table:a}")
            if self.table:
                base = f"{self.table:qa}.{base}"

        else:
            base = self.name if not self.alias else self.alias
            if "q" in format_spec:
                base = f'"{base}"'
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
        return f"{self.join_type} {self.table:qj} ON {self.left_on:qj} = {self.right_on:qj}"


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
                    f"({str(child)})" if child else "" for child in self.children
                )
            else:
                return str(self.filter_type).join(str(child) for child in self.children)

    def to_json(self):
        if self.filter_type == FilterType.LEAF:
            return self.expression
        else:
            return {
                "filter_type": self.filter_type,
                "children": [child.to_json() for child in self.children],
            }

    @staticmethod
    def from_json(json):
        if isinstance(json, str):
            return FilterExpression(expression=json)
        else:
            return FilterExpression(
                filter_type=json["filter_type"],
                children=[
                    FilterExpression.from_json(child) for child in json["children"]
                ],
            )


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
            joins = " ".join(map(lambda e: f"{e}", self.joins))

        q = f"SELECT {', '.join(map(lambda f:f'{f:qsa}', self.fields))} FROM {self.main_table:s} {joins}{filt}{order} LIMIT {self.limit} OFFSET {self.offset}"

        if format_spec == "p":
            q = f"({q})"
        print(q)
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

    instance_count = 0

    def __init__(self, conn: db.DuckDBPyConnection = None) -> None:
        super().__init__()

        Query.instance_count += 1
        # This is supposed to be a singleton. Dirty hack to enforce it
        if Query.instance_count > 1:
            print("Only one instance of Query is allowed")
            sys.exit(1)

        self.datalake_path = None
        self.init_state()

        self.fields_changed.connect(self.update)
        self.filters_changed.connect(self.update)
        self.order_by_changed.connect(self.update)
        self.limit_changed.connect(self.update)
        self.offset_changed.connect(self.update)
        self.from_changed.connect(self.update)

        self.conn = conn

    def init_state(self):
        # When we create a new Query, we want to reset everything, except for the datalake path...
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

        self.current_validation_name = None

    # Unused
    def add_field(self, field: Union[str, Field]):
        if isinstance(field, str):
            field = Field(field, None)
        self.fields.append(field)
        self.fields_changed.emit()

        return self

    # Unused
    def get_fields(self) -> List[Field]:
        return self.fields

    def set_fields(self, fields: List[Field]):
        self.fields = fields
        self.fields_changed.emit()

        return self

    def clear_fields(self):
        self.fields.clear()
        return self

    # Unused
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
        if not files:
            return self
        self.main_table = Table(
            f"read_parquet({duck_db_literal_string_list(files)})",
            "main_table",
            quoted=False,
        )
        self.from_changed.emit()
        return self

    def get_table_validation_name(self) -> str:
        return self.current_validation_name

    def set_table_validation_name(self, name: str):
        self.current_validation_name = name
        return self

    def add_join(self, join: Join):
        self.additional_tables[join.table.get_alias()] = join
        self.from_changed.emit()
        return self

    def clear_additional_tables(self):
        self.additional_tables.clear()
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
        field = Field("COUNT(*)", alias="count_star", is_expression=True)

        q = Select(
            fields=[field],
            main_table=self.main_table,
            additional_tables=list(self.additional_tables.values()),
            filters=self.filter,
        )
        return str(q)

    def is_valid(self):
        return (
            bool(self.main_table)
            and bool(self.fields)
            and self.datalake_path
            and self.conn
        )

    def to_do(self):
        if not self.datalake_path:
            return "Please select a datalake path"
        if not self.main_table:
            return "Please select a main table"
        if not self.fields:
            return "Please select some fields"
        if not self.conn:
            return "Please connect to the database"

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
        except db.Error as e:
            print(e)
            print(self.select_query())
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
        print(self.row_count)
        # print caller function (using python reflection)
        print(sys._getframe().f_back.f_code.co_name)
        self.page_count = self.row_count // self.limit
        if self.row_count % self.limit > 0:
            self.page_count = self.page_count + 1
        if self.current_page > self.page_count:
            self.set_page(self.page_count)
            self.update()  # TODO: Fix edge case
        self.blockSignals(False)
        self.query_changed.emit()

    def set_additional_tables(self, tables: dict):
        self.additional_tables = tables
        self.from_changed.emit()
        return self

    def set_datalake_path(self, path: str):
        if not os.path.isdir(path):
            return self
        os.chdir(path)
        self.datalake_path = path
        self.query_changed.emit()
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
                    "datalake_path": self.datalake_path,
                    "current_validation_name": self.current_validation_name,
                },
                f,
            )

    @staticmethod
    def load(filename: Path) -> "Query":
        with open(filename, "rb") as f:
            self_dic = pickle.load(f)
            q = Query()
            q.mute()
            # q.set_fields(self_dic["fields"])
            # q.main_table = self_dic["main_table"]
            # q.set_additional_tables(self_dic["additional_tables"])
            # q.set_filter(self_dic["filter"])
            # q.set_order_by(self_dic["order_by"])
            # q.set_limit(self_dic["limit"])
            # q.set_offset(self_dic["offset"])
            q.set_datalake_path(self_dic["datalake_path"])
            # q.set_table_validation_name(self_dic["current_validation_name"])
            q.unmute()
            return q


if __name__ == "__main__":
    pass
