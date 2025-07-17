import logging

import PySide6.QtWidgets as qw

import app as ap
import order_by.order_by_model as obm
import order_by.order_by_widget as obw
import query.query_component as q
from component_registry import register_app_component

LOGGER = logging.getLogger(__name__)


@register_app_component(
    name="order_by", policy="singleton", instantiation_time="demand"
)
class OrderByComponent(ap.AppComponent):

    component_name = "order_by"

    def __init__(self, app: ap.App, instance_name: str):
        super().__init__(app, instance_name)
        self.model = obm.OrderByModel(self)
        self.model.model_changed.connect(self.on_order_by_changed)

        self.query: "q.QueryComponent" = None

        self.app.selected_query_changed.connect(self.on_selected_query_changed)

        self.order_by_widget = obw.OrderByWidget(self.app, self)
        self.order_by_widget.setWindowTitle(self.app.translate("Order by selection"))

    def on_selected_query_changed(self):
        query: "q.QueryComponent" = self.app.get_current_query()

        if query is self.query:
            return

        if self.query is not None:
            self.query.closing.disconnect(self.on_selected_query_closing)
            self.query.query_changed.disconnect(self.on_query_changed)

        self.query = query
        if self.query is not None:
            self.query.closing.connect(self.on_selected_query_closing)
            self.query.query_changed.connect(self.on_query_changed)

        self.on_query_changed()

    def on_selected_query_closing(self):
        self.query = None
        self.model.load([])

    def on_query_changed(self):
        if self.query is None:
            self.model.load([])
            return

        order_by = self.query.get_order_by()
        if order_by is None:
            self.model.load([])
        else:
            self.model.load(order_by)

    def widget(self) -> qw.QWidget:
        return self.order_by_widget

    def get_field_names(self):
        if self.query is None:
            return []
        return self.query.get_fields()

    def on_order_by_changed(self):
        if self.query is not None:
            self.query.set_order_by(self.model.get_data()).commit()

    def close_component(self):
        self.app.selected_query_changed.disconnect(self.on_selected_query_changed)
        super().close_component()

    def __del__(self):
        LOGGER.debug("OrderByComponent deleted")
