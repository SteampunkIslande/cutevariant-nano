import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import app as ap
import order_by.order_by_model as obm
import order_by.order_by_widget as obw
import query.query_component as q


class OrderByComponent(ap.AppComponent):

    def __init__(
        self, app: ap.App, instance_name: str, parent_component: "ap.AppComponent"
    ):
        super().__init__(app, instance_name, parent_component)
        self.model = obm.OrderByModel(self)
        self.order_by_widget = obw.OrderByWidget(self.app, self)

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

    def emit_order_by_changed(self):
        self.broadcast.emit(
            "order_by_changed",
            "order_by",
            self.instance_name,
            {"order_by_expression": self.model.get_data()},
        )

    def generic_receiver(
        self,
        action: str,
        sender_component_name: str,
        sender_instance_name: str,
        payload: dict,
    ):
        if action == "query_order_by_changed":
            # We are concerned
            if sender_component_name == self.parent_component.get_instance_name():
                self.model.load(payload["order_by_expression"])
        return

    def get_field_names(self):
        query_component: q.QueryComponent = self.app.get_component(
            "query", self.parent_component.get_instance_name()
        )
        pass


def register_component():
    return "order_by", {
        "instantiation_policy": "multi",
        "instantiate_on": "demand",
        "class": OrderByComponent,
    }
