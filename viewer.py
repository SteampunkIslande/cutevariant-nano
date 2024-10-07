#!/usr/bin/env python


from pathlib import Path

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

from commons import get_user_prefs_file, load_user_prefs, save_user_prefs
from datalake import DataLake
from inspector import Inspector
from query import Query
from query_table_widget import QueryTableWidget


class MainWindow(qw.QMainWindow):

    def __init__(self):
        super().__init__()

        self.load_previous_session()

        self.query_table_widget = QueryTableWidget(self.validation_query)
        self.inspector = Inspector(self.datalake)

        self.main_widget = qw.QSplitter(qc.Qt.Orientation.Horizontal)
        self.main_widget.addWidget(self.inspector)
        self.main_widget.addWidget(self.query_table_widget)

        self.setCentralWidget(self.main_widget)

        self.menu = self.menuBar()

        self.file_menu = self.menu.addMenu(qc.QCoreApplication.tr("Fichier"))
        self.file_menu.addAction(
            qc.QCoreApplication.tr("Ouvrir un datalake"), self.open_datalake
        )
        # Open preferences folder
        self.file_menu.addAction(
            qc.QCoreApplication.tr("Ouvrir le dossier de préférences"),
            lambda: qg.QDesktopServices.openUrl(
                qc.QUrl.fromLocalFile(get_user_prefs_file().parent)
            ),
        )

        self.validation_query.query_changed.connect(self.on_query_changed)
        self.on_query_changed()

    def load_previous_session(self):
        prefs = self.get_user_prefs()
        if "last_session" not in prefs:
            self.datalake = DataLake()
            self.validation_query = Query(self.datalake, self)
            self.datalake.add_query("validation", self.validation_query)
        else:
            self.datalake = DataLake.load(Path(prefs["last_session"]))
            self.validation_query = self.datalake.get_query("validation")
            self.validation_query.init_state()

    def closeEvent(self, event: qg.QCloseEvent):
        user_prefs_folder = get_user_prefs_file().parent
        user_prefs_folder.mkdir(parents=True, exist_ok=True)

        # Save last query
        self.datalake.save(user_prefs_folder / "last_session.json")
        save_user_prefs({"last_session": str(user_prefs_folder / "last_session.json")})
        event.accept()

    def on_query_changed(self):
        self.setWindowTitle(
            f"ParquetViewer - {self.validation_query.get_editable_table_human_readable_name()}"
        )

    def get_user_prefs(self):
        return load_user_prefs()

    def open_datalake(self):
        if self.datalake.datalake_path:
            datalake_folder = qw.QFileDialog.getExistingDirectory(
                self,
                qc.QCoreApplication.tr("Ouvrir un datalake"),
                self.datalake.datalake_path,
            )
        else:
            datalake_folder = qw.QFileDialog.getExistingDirectory(
                self, qc.QCoreApplication.tr("Ouvrir un datalake"), str(Path.home())
            )
        if not datalake_folder:
            return
        self.datalake.set_datalake_path(datalake_folder)


if __name__ == "__main__":
    app = qw.QApplication([])

    app.setOrganizationName("CharlesMB")
    app.setApplicationName("ParquetViewer")

    window = MainWindow()
    window.show()

    app.exec()
