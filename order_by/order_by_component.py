import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import app as ap
from order_by.order_by_widget import OrderByWidget


class OrderByComponent(ap.AppComponent):

    def __init__(
        self, app: ap.App, instance_name: str, parent_component: "ap.AppComponent"
    ):
        super().__init__(app, instance_name, parent_component)

        self.order_by_widget = OrderByWidget(self.app, self.parent_component)

    def get_instance_name(self) -> str:
        return self.instance_name

    def load_from_session(self, session: dict):
        return

    def save_to_session(self) -> dict:
        return {}

    def on_start(self):
        return

    def widget(self) -> qw.QWidget:
        return self.order_by_widget

    def get_signal(self, signal_name: str) -> qc.SignalInstance:
        return

    def get_menubar_entries(self) -> list[tuple[str, qg.QAction]]:
        return []

    def get_contextmenu_entries(self, local_info: dict) -> list[tuple[str, qg.QAction]]:
        return []


def register_component():
    return "order_by", {
        "instantiation_policy": "multi",
        "instantiate_on": "demand",
        "class": OrderByComponent,
    }
