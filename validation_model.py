import PySide6.QtCore as qc

import duckdb as db

from pathlib import Path

from typing import List

from commons import duck_db_literal_string_list

from query import Query


def initialize_database(database: Path):

    # If the database already exists, we shouldn't initialize it
    if database.exists():
        return
    conn = db.connect(str(database))
    conn.sql(
        "CREATE TABLE validations (parquet_files TEXT[], sample_names TEXT[], username TEXT, validation_name TEXT, table_uuid TEXT, creation_date DATETIME, completed BOOLEAN)"
    )
    conn.sql(
        "CREATE TYPE COMMENT AS STRUCT(comment TEXT, username TEXT, creation_timestamp TIMESTAMP)"
    )
    return conn


def add_validation_table(
    conn: db.DuckDBPyConnection,
    validation_name: str,
    username: str,
    parquet_files: List[str],
    sample_names: List[str],
):
    table_uuid = (
        conn.sql("SELECT ('validation_' || uuid()) as uuid").pl().to_dicts()[0]["uuid"]
    )
    conn.sql(
        f"INSERT INTO validations VALUES ({duck_db_literal_string_list(parquet_files)}, {duck_db_literal_string_list(sample_names)}, '{username}', '{validation_name}', {table_uuid}, NOW(), FALSE)"
    )
    conn.sql(
        f"CREATE TABLE {table_uuid} (accepted BOOLEAN, comment COMMENT, tags TEXT[])"
    )


class ValidationModel(qc.QAbstractTableModel):

    def __init__(self, query: Query, parent: qc.QObject | None = ...) -> None:
        super().__init__(parent)
        self.query = query
        self.headers = []
        self._data = []

    def data(self, index: qc.QModelIndex, role: int) -> str | None:
        if role == qc.Qt.ItemDataRole.DisplayRole:
            return self._data[index.row()][index.column()]
        if role == qc.Qt.ItemDataRole.UserRole and index.column() == 0:
            if "table_uuid" in self.headers:
                return self._data[index.row()][self.headers.index("table_uuid")]

    def rowCount(self, parent: qc.QModelIndex) -> int:
        if parent.isValid():
            return 0
        return len(self._data)

    def columnCount(self, parent: qc.QModelIndex) -> int:
        if parent.isValid():
            return 0
        if self._data:
            return len(self._data[0])
        return 0

    def headerData(
        self, section: int, orientation: qc.Qt.Orientation, role: int
    ) -> str | None:
        if section >= len(self.headers) or section < 0:
            return None
        if role == qc.Qt.ItemDataRole.DisplayRole:
            if orientation == qc.Qt.Orientation.Horizontal:
                return self.headers[section]

    def new_validation(
        self,
        validation_name: str,
        username: str,
        parquet_files: List[str],
        sample_names: List[str],
    ):
        if self.query.conn:
            self.beginInsertRows(qc.QModelIndex(), len(self._data), len(self._data))
            add_validation_table(
                self.query.conn, validation_name, username, parquet_files, sample_names
            )
            self.endInsertRows()

    def set_query(self, query: Query):
        self.query = query
        self.update()

    def update(self) -> None:
        self.beginResetModel()
        self.headers = []
        self._data = []
        if self.query.conn:
            query_res = self.query.conn.sql("SELECT * FROM validations").pl()
            self.headers = query_res.columns
            self._data = [tuple(v for v in d.values()) for d in query_res.to_dicts()]
        self.endResetModel()
