import os

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import app


class Datalake(app.AppComponent):

    folder_changed = qc.Signal(int, str)

    def __init__(self, app: app.App, instance_id: int):
        self.app = app
        self.instance_id = instance_id

        self.signals_dict = {"folder_changed": self.folder_changed}

        self.datalake_path = None

    def load_from_session(self, session):
        self.datalake_path = session.get("datalake_path")
        if not os.path.isdir(self.datalake_path):
            self.datalake_path = None
        self.folder_changed.emit()

    def save_to_session(self):
        return {"datalake_path": self.datalake_path}

    def on_start(self):
        pass

    def widget(self):
        return None

    def get_signal(self, signal_name: str):
        return self.signals_dict.get(signal_name)

    def get_menubar_entries(self):
        set_datalake_path_action = qg.QAction(self.app.translate("Open datalake"))
        set_datalake_path_action.triggered.connect(self.set_datalake_path)
        return [(self.app.translate("File"), set_datalake_path_action)]

    def get_contextmenu_entries(self, local_info: dict):
        return []

    def set_datalake_path(self):
        existing_dir = qw.QFileDialog.getExistingDirectory(self.app.window())
        if os.path.isdir(existing_dir):
            self.datalake_path = existing_dir
            self.folder_changed.emit(self.instance_id, self.datalake_path)

    def relative_to_absolute(self, path: str) -> str:
        if self.datalake_path:
            return os.path.join(self.datalake_path, path)


def register_component():
    return "datalake", {
        "instantiation_policy": "singleton",
        "instantiate_on": "setup",
        "context_menu_actions": {},
        "component_type": ["LOGICAL"],
        "class": Datalake,
    }
