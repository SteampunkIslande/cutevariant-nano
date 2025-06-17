import PySide6.QtWidgets as qw

import app as ap
import order_by.order_by_model as obm
import order_by.order_by_widget as obw
from component_registry import register_app_component


@register_app_component(name="order_by", policy="multi", instantiation_time="demand")
class OrderByComponent(ap.AppComponent):

    component_name = "order_by"

    def __init__(self, app: ap.App, instance_name: str):
        super().__init__(app, instance_name)
        self.model = obm.OrderByModel(self)
        self.order_by_widget = obw.OrderByWidget(self.app, self)
        self.order_by_widget.setWindowTitle(self.app.translate("Order by selection"))

        self.model.model_changed.connect(self.emit_order_by_changed)

        self.field_names = []

    def on_start(self):
        # query: q.QueryComponent = self.app.get_component("query", query_component_name)

        # self.field_names = query.get_all_fields()
        pass

    def widget(self) -> qw.QWidget:
        return self.order_by_widget

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

    def cleanup(self):
        self.model = None
        self.order_by_widget = None
