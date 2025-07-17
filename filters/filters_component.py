import logging

import app
import filters.filters_model as fltm
import filters.filters_widget as fltw
import query.query_component as q
from component_registry import register_app_component

LOGGER = logging.getLogger(__name__)


@register_app_component(name="filters", policy="singleton", instantiation_time="demand")
class FiltersComponent(app.AppComponent):

    component_name = "filters"

    def __init__(self, app: app.App, instance_name: str):
        super().__init__(app, instance_name)

        self.model = fltm.FilterModel(self)
        self.model.load(
            {
                "filter_type": "ROOT",
                "children": [{"filter_type": "AND", "children": []}],
            }
        )
        self.model.model_changed.connect(self.on_filters_changed)

        self.query: q.QueryComponent = None

        self.app.selected_query_changed.connect(self.on_selected_query_changed)

        self.filters_widget = fltw.FiltersWidget(self.app, self, self.model)
        self.filters_widget.setWindowTitle(self.app.translate("Filters selection"))

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
        self.model.load(None)

    def on_query_changed(self):
        if self.query is None:
            self.model.load(None)
            return

        if self.query.get_filter() != self.model.to_dict():
            self.model.load(self.query.get_filter())

    def add_expression(self, expression: str):
        self.model.add_filter(expression)

    def on_filters_changed(self):
        if self.query:
            self.query.set_filter(self.model.to_dict()).commit()

    def widget(self):
        return self.filters_widget

    def close_component(self):
        self.app.selected_query_changed.disconnect(self.on_selected_query_changed)

        super().close_component()

    def __del__(self):
        LOGGER.debug("FiltersComponent deleted")
