import logging
from typing import TYPE_CHECKING

import app
import fields.fields_widget as fldw

if TYPE_CHECKING:
    import query.query_component as q

from component_registry import register_app_component
from fields import fields_model as fldm

LOGGER = logging.getLogger(__name__)


@register_app_component(name="fields", policy="singleton", instantiation_time="demand")
class FieldsComponent(app.AppComponent):

    component_name = "fields"

    def __init__(self, app: "app.App", instance_name: str):
        super().__init__(app, instance_name)

        self.model = fldm.FieldsModel(self)
        self.model.dataChanged.connect(self.on_selected_fields_changed)
        self.model.rowsMoved.connect(self.on_selected_fields_changed)

        self.datalake_component = self.app.get_component("datalake")

        self.query = None

        self.app.selected_query_changed.connect(self.on_selected_query_changed)

        self.fields_widget = fldw.FieldsWidget(self.app, self)
        self.fields_widget.setWindowTitle(self.app.translate("Fields selection"))

    def widget(self):
        return self.fields_widget

    def on_selected_fields_changed(self):
        if self.model.get_all_fields() != self.query.get_fields():
            self.query.set_fields(self.model.get_all_fields()).commit()

    def on_selected_query_changed(self):
        query: "q.QueryComponent" = self.app.get_current_query()

        if query is self.query:
            LOGGER.warning(
                "on_selected_query_changed called with the same query, ignoring."
            )
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

        if self.query.get_fields() != self.model.get_all_fields():
            self.model.load(self.query.get_fields())

    def close_component(self):

        self.app.selected_query_changed.disconnect(self.on_selected_query_changed)

        super().close_component()

    def __del__(self):
        LOGGER.debug("FieldsComponent deleted")
