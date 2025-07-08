import glob
import logging
import os
import shutil
import typing
from pathlib import Path

import duckdb as db
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import app
from component_registry import register_app_component

LOGGER = logging.getLogger(__name__)


class DatabaseConnection:

    def __init__(self, datalake: "DatalakeComponent", database_name: str):
        database = Path(datalake.datalake_path) / f"{database_name}.db"

        # If the database already exists, we shouldn't initialize it
        if database.exists():
            self.conn = db.connect(str(database))
        else:
            self.conn = db.connect(str(database))
            self.init_conn()

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            info = (exc_type, exc_val, exc_tb)
            LOGGER.error("Database connection error", exc_info=info)
            return False

    def init_conn(self):
        self.conn.sql(
            "CREATE TABLE validations (parquet_files TEXT[], sample_names TEXT[], gene_names TEXT[], username TEXT, validation_name TEXT, table_uuid TEXT, creation_date DATETIME, completed BOOLEAN, validation_method TEXT)"
        )
        self.conn.sql(
            "CREATE TYPE COMMENT AS STRUCT(comment TEXT, username TEXT, creation_timestamp TIMESTAMP)"
        )


@register_app_component(name="datalake", policy="singleton", instantiation_time="setup")
class DatalakeComponent(app.AppComponent):

    component_name = "datalake"

    def __init__(
        self,
        app: "app.App",
        instance_name: str,
    ):
        super().__init__(app, instance_name)

        self.set_datalake_path_action = qg.QAction(self.app.translate("Open datalake"))
        self.set_datalake_path_action.triggered.connect(self.set_datalake_path)

        self.update_datalake_action = qg.QAction(
            self.app.translate("Update datalake (genno)")
        )
        self.update_datalake_action.triggered.connect(self.genno_update_datalake)

        self.datalake_path = None

    def load_from_session(self, session: dict):

        new_datalake_path = session.get("datalake_path", None)
        if new_datalake_path is None:
            LOGGER.warning(
                "No datalake path found in session. Please set the datalake path. Datalake path didn't change."
            )
            return
        if not os.path.isdir(new_datalake_path):
            self.datalake_path = None
        else:
            self.datalake_path = new_datalake_path

        self.app.update_app(
            {
                "action": "datalake_path_changed",
                "sender_component_name": self.component_name,
                "sender_instance_name": self.instance_name,
                "data": {"datalake_path": self.datalake_path},
            }
        )

    def save_to_session(self):
        return {"datalake_path": self.datalake_path}

    def get_menubar_entries(self):

        return [
            (self.app.translate("File"), self.set_datalake_path_action),
            (self.app.translate("File"), self.update_datalake_action),
        ]

    def genno_list_runs(self):
        return [
            os.path.basename(r).split(".")[0]
            for r in glob.glob(
                os.path.join(self.datalake_path, "genotypes/runs/*.parquet")
            )
        ]

    def genno_update_datalake(self):
        from datalake.datalake_import_genno import import_parquet, init_datalake

        incoming_parquet_file = qw.QFileDialog.getOpenFileName(
            self.app.window(),
            self.app.translate("Select incoming parquet file"),
            "",
            self.app.translate("Parquet files (*.parquet)"),
        )[0]
        if not incoming_parquet_file or not os.path.isfile(incoming_parquet_file):
            qw.QMessageBox.warning(
                self.app.window(),
                self.app.translate("Import Error"),
                self.app.translate(
                    "No incoming parquet file selected. Nothing imported."
                ),
            )
            return

        run_name = Path(incoming_parquet_file).name.split(".")[0]

        existing_runs = self.genno_list_runs()
        if run_name in existing_runs:
            qw.QMessageBox.warning(
                self.app.window(),
                self.app.translate("Import Error"),
                self.app.translate(
                    "Run {run_name} already exists in datalake. Nothing imported."
                ).format(run_name=run_name),
            )
            return

        control_file = os.path.join(
            self.datalake_path, "vcf_extracted", run_name + ".parquet"
        )

        init_datalake(Path(self.datalake_path))

        shutil.copy(
            incoming_parquet_file,
            control_file,
        )
        try:
            import_parquet(Path(self.datalake_path), Path(control_file))
        except Exception as e:
            qw.QMessageBox.critical(
                self.app.window(),
                self.app.translate("Import Error"),
                self.app.translate(
                    "Error importing {incoming_parquet_file}: {e}. The datalake is now in an undefined state..."
                ).format(incoming_parquet_file=incoming_parquet_file, e=e),
            )
            os.remove(control_file)
            return
        qw.QMessageBox.information(
            self.app.window(),
            self.app.translate("Import Success"),
            self.app.translate(
                "Run {run_name} imported successfully. The datalake is now up to date."
            ).format(run_name=run_name),
        )

    def set_datalake_path(self):
        existing_dir = qw.QFileDialog.getExistingDirectory(self.app.window())
        if os.path.isdir(existing_dir):
            self.datalake_path = existing_dir
            self.app.update_app(
                {
                    "action": "datalake_path_changed",
                    "sender_component_name": self.component_name,
                    "sender_instance_name": self.instance_name,
                    "data": {"datalake_path": self.datalake_path},
                }
            )

    def relative_to_absolute(self, path: str) -> str:
        if self.datalake_path:
            return os.path.join(self.datalake_path, path)

    def run_with_connection(
        self,
        database_name,
        func: typing.Callable[[db.DuckDBPyConnection, typing.Any], typing.Any],
        *args,
        **kwargs,
    ):
        """
        Executes a function within the context of a database connection.
        This method establishes a connection to the specified database,
        executes the provided function with the connection and any additional
        arguments, and ensures that the connection is properly closed afterwards.
        Args:
            database_name (str): The name of the database to connect to.
            func (callable): The function to execute with the database connection.
            *args: Variable length argument list to pass to the function.
            **kwargs: Arbitrary keyword arguments to pass to the function.
        """
        with DatabaseConnection(self, database_name) as conn:
            return func(conn, *args, **kwargs)

    def close_component(self):

        super().close_component()

        self.set_datalake_path_action = None
        self.update_datalake_action = None
