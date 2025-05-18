import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import app as ap
import order_by.order_by_model as obm
import order_by.order_by_widget as obw


class OrderByComponent(ap.AppComponent):

    def __init__(self, app: ap.App, instance_name: str):
        super().__init__(app, instance_name)
        self.model = obm.OrderByModel(self)
        self.order_by_widget = obw.OrderByWidget(self.app, self)

        self.model.model_changed.connect(self.emit_order_by_changed)

        self.field_names = []

    def get_instance_name(self) -> str:
        return self.instance_name

    def load_from_session(self, session: dict):
        return

    def save_to_session(self) -> dict:
        return {}

    def on_start(self):
        # query: q.QueryComponent = self.app.get_component("query", query_component_name)

        # self.field_names = query.get_all_fields()
        pass

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
        # if action == "query:order_by_changed":
        #     if sender_instance_name == self.parent_component.get_instance_name():
        #         self.model.load(payload["order_by"])
        # if action == "query_field_names_changed":
        #     if sender_instance_name == self.parent_component.get_instance_name():
        #         self.field_names = payload["field_names"]
        return

    def get_field_names(self):
        return self.field_names


def register_component():
    return "order_by", {
        "instantiation_policy": "multi",
        "instantiate_on": "demand",
        "class": OrderByComponent,
    }
