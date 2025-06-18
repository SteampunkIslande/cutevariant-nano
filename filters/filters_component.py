import app
import filters.filters_model as fltm
import filters.filters_widget as fltw
from component_registry import register_app_component


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
        self.model.model_changed.connect(self.emit_filters_changed)
        self.filters_widget = fltw.FiltersWidget(self.app, self, self.model)

        self.filters_widget.setWindowTitle(self.app.translate("Filters selection"))

    def add_expression(self, expression: str):
        self.model.add_filter(expression)

    def emit_filters_changed(self):
        self.broadcast.emit(
            "filters_changed",
            "filters",
            self.instance_name,
            {"filter_tree": self.model.to_dict()},
        )

    def widget(self):
        return self.filters_widget

    def generic_receiver(
        self, action, sender_component_name, sender_instance_name, payload
    ):
        pass

    def cleanup(self):
        self.model = None
        self.filters_widget = None

    def __del__(self):
        print("FiltersComponent deleted")
