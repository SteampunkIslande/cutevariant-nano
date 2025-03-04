import datetime
from pathlib import Path
from typing import List

import duckdb as db
import polars as pl
import PySide6.QtCore as qc

import app as ap
import datalake.datalake_component as dl
from commons import duck_db_literal_string_list

VALIDATION_TABLE_COLUMNS = {
    v: i
    for i, v in enumerate(
        [
            "parquet_files",
            "sample_names",
            "gene_names",
            "username",
            "validation_name",
            "table_uuid",
            "creation_date",
            "completed",
            "last_step",
        ]
    )
}


def finish_validation(conn: db.DuckDBPyConnection, table_uuid: str):
    conn.sql(
        f"UPDATE validations SET completed = TRUE WHERE table_uuid = '{table_uuid}'"
    )


def new_validation(
    conn: db.DuckDBPyConnection,
    validation_name: str,
    username: str,
    file_names: List[str],
    sample_names: List[str],
    gene_names: List[str],
    validation_method: str,
):
    # Generate a unique identifier for the new table
    table_uuid = (
        conn.sql("SELECT ('validation_' || uuid()) as uuid").pl().to_dicts()[0]["uuid"]
    )
    try:
        conn.begin()
        conn.sql(
            f"INSERT INTO validations VALUES ({duck_db_literal_string_list(file_names)}, {duck_db_literal_string_list(sample_names) if sample_names else 'NULL'}, {gene_names if gene_names else 'NULL'} , '{username}', '{validation_name}', '{table_uuid}', NOW(), FALSE, '{validation_method}')"
        )
        conn.sql(
            f"CREATE TABLE '{table_uuid}' (validation_hash UBIGINT,sample_name TEXT,run_name TEXT,transcript_ID TEXT,variant_hash UBIGINT, accepted BOOLEAN,comment COMMENT[], tags TEXT[], acmg_classification TEXT, clnacc TEXT, clnsig TEXT, distribution_anomalie TEXT)"
        )
        conn.commit()
    except db.Error as e:
        print(e)
        # No matter what the exact error is, we should rollback the transaction
        conn.rollback()


def insert_validation_data(
    conn: db.DuckDBPyConnection,
    table_uuid: str,
    validation_hash: int,
    sample_name: str,
    run_name: str,
    transcript_ID: str,
    variant_hash: int,
    accepted: bool,
    comment: str,
    tags: List[str],
    acmg_classification: str,
    distribution_anomalie: str,
):
    is_validation_hash_present = (
        conn.sql(
            f"""SELECT COUNT(*) FROM "{table_uuid}" WHERE validation_hash = {validation_hash}"""
        ).fetchone()[0]
        == 1
    )

    username = qc.QDir().home().dirName()

    if not is_validation_hash_present:
        conn.sql(
            f"""INSERT INTO "{table_uuid}" (validation_hash,sample_name,run_name, transcript_ID, variant_hash) VALUES ({validation_hash}, '{sample_name}', '{run_name}', '{transcript_ID}', '{variant_hash}')"""
        )

    conn.sql(
        f"""UPDATE "{table_uuid}" SET accepted = {accepted}, comment = comment || [row('{comment}','{username}',NOW())], tags = {duck_db_literal_string_list(tags)}, acmg_classification = '{acmg_classification}', distribution_anomalie = '{distribution_anomalie}' WHERE validation_hash = {validation_hash}"""
    )


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

    model_updated = qc.Signal()

    def __init__(
        self, app: ap.App, datalake: dl.Datalake, parent: qc.QObject | None = ...
    ) -> None:
        super().__init__(parent)
        self.app = app
        self.datalake = datalake
        self.headers = []
        self._data = []

        self.update_query = "SELECT * FROM validations"

        self.datalake.folder_changed.connect(self.update)
        if self.datalake.datalake_path:
            self.update()

    def data(
        self, index: qc.QModelIndex, role: int = qc.Qt.ItemDataRole.DisplayRole
    ) -> str | None:
        if role == qc.Qt.ItemDataRole.DisplayRole:
            res = self._data[index.row()][index.column()]
            if isinstance(res, bool):
                res = self.app.translate("Yes") if res else self.app.translate("No")
            if isinstance(res, datetime.datetime):
                res = res.strftime(self.app.translate("%d/%m/%Y %H:%M:%S"))
            if (
                self.headerData(
                    index.column(),
                    qc.Qt.Orientation.Horizontal,
                    qc.Qt.ItemDataRole.DisplayRole,
                )
                == "parquet_files"
            ):
                res = "\n".join([Path(r).stem for r in res])

            if isinstance(res, list):
                res = "\n".join(res)
            return res
        if role == qc.Qt.ItemDataRole.UserRole:
            return {k: v for k, v in zip(self.headers, self._data[index.row()])}

    def rowCount(self, parent: qc.QModelIndex = qc.QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._data)

    def columnCount(self, parent: qc.QModelIndex = qc.QModelIndex()) -> int:
        if parent.isValid():
            return 0
        if self._data:
            return len(self._data[0])
        return 0

    def set_hide_completed(self, hide: bool):
        if hide:
            self.update_query = "SELECT * FROM validations WHERE completed = False"
        else:
            self.update_query = "SELECT * FROM validations"
        self.update()

    def headerData(
        self,
        section: int,
        orientation: qc.Qt.Orientation,
        role: int = qc.Qt.ItemDataRole.DisplayRole,
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
        file_names: List[str],
        sample_names: List[str],
        gene_names: List[str],
        validation_method: str,
    ):
        if self.datalake.datalake_path:
            self.datalake.run_with_connection(
                "validation",
                new_validation,
                validation_name,
                username,
                file_names,
                sample_names,
                gene_names,
                validation_method,
            )
            self.update()

    def insert_validation_data(
        self,
        table_uuid: str,
        validation_hash: int,
        sample_name: str,
        run_name: str,
        transcript_ID: str,
        variant_hash: int,
        accepted: bool,
        comment: str,
        tags: List[str],
        acmg_classification: str,
        distribution_anomalie: str,
    ):
        if self.datalake.datalake_path:
            self.datalake.run_with_connection(
                "validation",
                insert_validation_data,
                table_uuid,
                validation_hash,
                sample_name,
                run_name,
                transcript_ID,
                variant_hash,
                accepted,
                comment,
                tags,
                acmg_classification,
                distribution_anomalie,
            )

    def update(self) -> None:
        self.beginResetModel()
        self.headers = []
        self._data = []
        query_res: pl.DataFrame = self.datalake.run_with_connection(
            "validation",
            lambda conn: conn.sql(self.update_query).pl(),
        )
        self.headers = query_res.columns
        self._data = [tuple(v for v in d.values()) for d in query_res.to_dicts()]
        self.endResetModel()
        self.model_updated.emit()
