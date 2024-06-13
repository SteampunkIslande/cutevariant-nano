import datetime
from pathlib import Path
from typing import List

import duckdb as db
import PySide6.QtCore as qc

from commons import duck_db_literal_string_list
from datalake import DataLake, get_database

VALIDATION_TABLE_COLUMNS = {
    "parquet_files": 0,
    "sample_names": 1,
    "username": 2,
    "validation_name": 3,
    "table_uuid": 4,
    "creation_date": 5,
    "completed": 6,
    "last_step": 7,
}


def add_validation_table(
    conn: db.DuckDBPyConnection,
    validation_name: str,
    username: str,
    parquet_files: List[str],
    sample_names: List[str],
    validation_method: str,
):
    table_uuid = (
        conn.sql("SELECT ('validation_' || uuid()) as uuid").pl().to_dicts()[0]["uuid"]
    )
    try:
        conn.sql(
            f"INSERT INTO validations VALUES ({duck_db_literal_string_list(parquet_files)}, {duck_db_literal_string_list(sample_names)}, '{username}', '{validation_name}', '{table_uuid}', NOW(), FALSE, 0, '{validation_method}')"
        )
        conn.sql(
            f"CREATE TABLE '{table_uuid}' (validation_hash BIGINT,sample_name TEXT,run_name TEXT,transcript_ID TEXT,accepted BOOLEAN,comment COMMENT[], tags TEXT[])"
        )
    except db.Error as e:
        print(e)
        # No matter what the exact error is, we should rollback the transaction
        # Manual rollback
        conn.sql(f"""DROP TABLE IF EXISTS "{table_uuid}" """)
        conn.sql(f"DELETE FROM validations WHERE table_uuid = '{table_uuid}'")


def get_validation_from_table_uuid(
    conn: db.DuckDBPyConnection, table_uuid: str
) -> dict:
    return (
        conn.sql(f"SELECT * FROM validations WHERE table_uuid = '{table_uuid}'")
        .pl()
        .to_dicts()[0]
    )


def get_validation_name_from_table_uuid(conn: db.DuckDBPyConnection, table_uuid: str):
    return (
        conn.sql(
            f"SELECT validation_name FROM validations WHERE table_uuid = '{table_uuid}'"
        )
        .pl()
        .to_dicts()[0]["validation_name"]
    )


class ValidationModel(qc.QAbstractTableModel):

    def __init__(self, datalake: DataLake, parent: qc.QObject | None = ...) -> None:
        super().__init__(parent)
        self.datalake = datalake
        self.headers = []
        self._data = []

        self.datalake.folder_changed.connect(self.update)
        if self.datalake.datalake_path:
            self.update()

    def data(self, index: qc.QModelIndex, role: int) -> str | None:
        if role == qc.Qt.ItemDataRole.DisplayRole:
            res = self._data[index.row()][index.column()]
            if isinstance(res, bool):
                res = "Yes" if res else "No"
            if isinstance(res, datetime.datetime):
                res = res.strftime("%d/%m/%Y %H:%M:%S")
            if (
                self.headerData(
                    index.column(),
                    qc.Qt.Orientation.Horizontal,
                    qc.Qt.ItemDataRole.DisplayRole,
                )
                == "parquet_files"
            ):
                res = ", ".join([Path(r).stem for r in res])

            if isinstance(res, list):
                res = ", ".join(res)
            return res
        if role == qc.Qt.ItemDataRole.UserRole and index.column() == 0:
            return {k: v for k, v in zip(self.headers, self._data[index.row()])}

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
        validation_method: str,
    ):
        if self.datalake.datalake_path:
            conn = get_database(Path(self.datalake.datalake_path) / "validation.db")
            add_validation_table(
                conn,
                validation_name,
                username,
                parquet_files,
                sample_names,
                validation_method,
            )
            self.update()
            conn.close()
        else:
            print("No connection to database")

    def update(self) -> None:
        self.beginResetModel()
        self.headers = []
        self._data = []
        conn = get_database(Path(self.datalake.datalake_path) / "validation.db")
        query_res = conn.sql("SELECT * FROM validations").pl()
        self.headers = query_res.columns
        self._data = [tuple(v for v in d.values()) for d in query_res.to_dicts()]
        self.endResetModel()
        conn.close()
