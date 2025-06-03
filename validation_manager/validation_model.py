import datetime
import os
from pathlib import Path

# Import différé pour résoudre la dépendance circulaire
from typing import TYPE_CHECKING, List

import duckdb as db
import polars as pl
import PySide6.QtCore as qc

import app as ap

if TYPE_CHECKING:
    from validation_manager.validation_manager_component import (
        ValidationManagerComponent,
    )

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
    **kwargs,
):

    conn.begin()
    try:

        is_validation_hash_present = (
            conn.sql(
                f"""SELECT COUNT(*) FROM "{table_uuid}" WHERE validation_hash = {validation_hash}"""
            ).fetchone()[0]
            == 1
        )

        username = qc.QDir().home().dirName()

        if not is_validation_hash_present:
            if not all(
                [
                    "sample_name" in kwargs,
                    "run_name" in kwargs,
                    "transcript_ID" in kwargs,
                    "variant_hash" in kwargs,
                ]
            ):
                raise ValueError(
                    "sample_name, run_name, transcript_ID and variant_hash are required"
                )

            conn.sql(
                f"""INSERT INTO "{table_uuid}" (validation_hash,sample_name,run_name, transcript_ID, variant_hash) VALUES ({validation_hash}, '{kwargs["sample_name"]}', '{kwargs["run_name"]}', '{kwargs["transcript_ID"]}', '{kwargs["variant_hash"]}')"""
            )

        comment_update = ""
        if "comment" in kwargs:
            comment_update = (
                f"comment = comment || [row('{kwargs['comment']}','{username}',NOW())]"
            )

        accepted_update = ""
        if "accepted" in kwargs:
            accepted_update = f"accepted = {kwargs['accepted']}"

        tags_update = ""
        if "tags" in kwargs:
            tags_update = f"tags = {duck_db_literal_string_list(kwargs['tags'])}"

        acmg_classification_update = ""
        if "acmg_classification" in kwargs:
            acmg_classification_update = (
                f"acmg_classification = '{kwargs['acmg_classification']}'"
            )

        distribution_anomalie_update = ""
        if "distribution_anomalie" in kwargs:
            distribution_anomalie_update = (
                f"distribution_anomalie = '{kwargs['distribution_anomalie']}'"
            )

        updates = ", ".join(
            filter(
                None,
                [
                    comment_update,
                    accepted_update,
                    tags_update,
                    acmg_classification_update,
                    distribution_anomalie_update,
                ],
            )
        )
        if updates:
            conn.sql(
                f"""UPDATE "{table_uuid}" SET {updates} WHERE validation_hash = {validation_hash}"""
            )
    except Exception as e:
        print(e)
        conn.rollback()
    else:
        conn.commit()


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

    def __init__(self, app: ap.App, parent_component: ap.AppComponent) -> None:
        super().__init__(parent_component)
        self.app = app
        self.parent_component: "ValidationManagerComponent" = parent_component
        self.headers = []
        self._data = []

        self.update_query = "SELECT * FROM validations"

    def data(
        self, index: qc.QModelIndex, role: int = qc.Qt.ItemDataRole.DisplayRole
    ) -> str | None:
        if role == qc.Qt.ItemDataRole.DisplayRole:
            res = self._data[index.row()][index.column()]
            if isinstance(res, bool):
                res = self.app.translate("Yes") if res else self.app.translate("No")
            if isinstance(res, datetime.datetime):
                res = res.strftime(self.app.translate("%m/%d/%Y %H:%M:%S"))
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
        datalake = self.parent_component.get_datalake()
        if datalake.datalake_path and os.path.exists(datalake.datalake_path):
            datalake.run_with_connection(
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

    def insert_validation_data(self, table_uuid: str, validation_hash: int, **kwargs):
        datalake = self.parent_component.get_datalake()
        if datalake.datalake_path and os.path.exists(datalake.datalake_path):
            datalake.run_with_connection(
                "validation",
                insert_validation_data,
                table_uuid,
                validation_hash,
                **kwargs,
            )

    def finish_validation(self, table_uuid: str):
        datalake = self.parent_component.get_datalake()
        if datalake.datalake_path and os.path.exists(datalake.datalake_path):
            datalake.run_with_connection(
                "validation",
                finish_validation,
                table_uuid,
            )
            self.update()

    def update(self) -> None:
        self.beginResetModel()
        self.headers = []
        self._data = []
        datalake = self.parent_component.get_datalake()
        if datalake.datalake_path and os.path.exists(datalake.datalake_path):
            query_res: pl.DataFrame = datalake.run_with_connection(
                "validation",
                lambda conn: conn.sql(self.update_query).pl(),
            )
            self.headers = query_res.columns
            self._data = [tuple(v for v in d.values()) for d in query_res.to_dicts()]
            self.endResetModel()
            self.model_updated.emit()
