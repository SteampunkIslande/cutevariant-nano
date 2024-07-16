import pickle
import sys
from pathlib import Path
from typing import Dict

import duckdb as db
import PySide6.QtCore as qc

import query as q


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
        self.queries: Dict[str, q.Query] = dict()

    def set_datalake_path(self, path: str):
        self.datalake_path = path
        self.folder_changed.emit()
        return self

    def add_query(self, name: str, query: "q.Query"):
        self.queries[name] = query

    def get_query(self, name: str) -> "q.Query":
        return self.queries.get(name)

    def relative_to_absolute(self, path: str) -> str:
        return str(Path(self.datalake_path) / path)

    def save(self, filename: Path):
        with open(filename, "wb") as f:
            pickle.dump(
                {
                    "datalake_path": self.datalake_path,
                    "queries": {k: v.to_json() for k, v in self.queries.items()},
                },
                f,
            )

    @staticmethod
    def load(filename: Path) -> "DataLake":
        with open(filename, "rb") as f:
            self_dic = pickle.load(f)
            datalake = DataLake()
            datalake.set_datalake_path(self_dic["datalake_path"])
            queries: Dict[str, dict] = self_dic["queries"]
            for name, serialized_query in queries.items():
                query = q.Query.from_json(serialized_query, datalake)
                datalake.add_query(name, query)
            return datalake

    def get_database(self, database_name: str):

        database = Path(self.datalake_path) / f"{database_name}.db"

        # If the database already exists, we shouldn't initialize it
        if database.exists():
            return db.connect(str(database))
        conn = db.connect(str(database))
        conn.sql(
            "CREATE TABLE validations (parquet_files TEXT[], sample_names TEXT[], gene_names TEXT[] , username TEXT, validation_name TEXT, table_uuid TEXT, creation_date DATETIME, completed BOOLEAN, validation_method TEXT)"
        )
        conn.sql(
            "CREATE TYPE COMMENT AS STRUCT(comment TEXT, username TEXT, creation_timestamp TIMESTAMP)"
        )
        return conn
