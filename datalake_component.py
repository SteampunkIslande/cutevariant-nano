import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

import app


class Datalake(app.AppComponent):

    folder_changed = qc.Signal(str)

    def __init__(self, app: app.App, instance_id: int):
        self.app = app
        self.instance_id = instance_id

        self.signals_dict = {"folder_changed": self.folder_changed}

    def widget(self):
        return None

    def on_start(self):
        pass

    def on_action_triggered(self):
        existing_dir = qw.QFileDialog.getExistingDirectory(self.app.window())

    def get_signal(self, signal_name: str):
        return self.signals_dict.get(signal_name)


def register_component():
    return "datalake", {
        "instantiation_policy": "singleton",
        "instantiate_on": "setup",
        "menubar_action": "File/Open datalake",
        "context_menu_actions": {},
        "class": Datalake,
    }
