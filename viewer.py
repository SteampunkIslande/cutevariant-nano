#!/usr/bin/env python


from pathlib import Path

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

from commons import load_user_prefs, save_user_prefs, get_user_prefs_file
from inspector import Inspector
from query import Query
from query_table_widget import QueryTableWidget


class MainWindow(qw.QMainWindow):

    def __init__(self):
        super().__init__()

        self.query = Query()

        self.query_table_widget = QueryTableWidget(self.query)
        self.inspector = Inspector(self.query)

        self.database = None

        self.main_widget = qw.QSplitter(qc.Qt.Orientation.Horizontal)
        self.main_widget.addWidget(self.inspector)
        self.main_widget.addWidget(self.query_table_widget)

        self.setCentralWidget(self.main_widget)

        self.menu = self.menuBar()

        self.file_menu = self.menu.addMenu("File")
        self.file_menu.addAction("Open datalake", self.open_datalake)

        self.load_previous_session()

    def load_previous_session(self):
        prefs = self.get_user_prefs()
        if "last_query" not in prefs:
            return
        self.query = Query.load(Path(prefs["last_query"]))

    def closeEvent(self, event: qg.QCloseEvent):
        user_prefs_folder = get_user_prefs_file().parent
        user_prefs_folder.mkdir(parents=True, exist_ok=True)

        # Save last query
        self.query.save(user_prefs_folder / "last_query.pickle")
        self.save_user_prefs(
            {"last_query": str(user_prefs_folder / "last_query.pickle")}
        )
        event.accept()

    def save_user_prefs(self, prefs: dict):
        save_user_prefs(prefs)

    def get_user_prefs(self):
        return load_user_prefs()

    def open_datalake(self):
        if "last_datalake" in self.get_user_prefs():
            last_datalake = self.get_user_prefs()["last_datalake"]
            datalake_folder = qw.QFileDialog.getExistingDirectory(
                self, "Open datalake", last_datalake
            )
        else:
            datalake_folder = qw.QFileDialog.getExistingDirectory(
                self, "Open datalake", str(Path.home())
            )
            self.save_user_prefs({"last_datalake": datalake_folder})
        if not datalake_folder:
            return
        self.query.set_datalake_path(datalake_folder)


if __name__ == "__main__":
    app = qw.QApplication([])

    app.setOrganizationName("CharlesMB")
    app.setApplicationName("ParquetViewer")

    window = MainWindow()
    window.show()

    app.exec()
