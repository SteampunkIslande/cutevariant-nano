import app
import filters.filters_model as fltm
import filters.filters_widget as fltw


class FiltersComponent(app.AppComponent):

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

    def add_expression(self, expression: str):
        self.model.add_filter(expression)

    def emit_filters_changed(self):
        self.broadcast.emit(
            "filters_changed",
            "filters",
            self.instance_name,
            {"filter_tree": self.model.to_dict()},
        )

    def generic_receiver(
        self, action, sender_component_name, sender_instance_name, payload
    ):
        pass

    def __del__(self):
        print("FiltersComponent deleted")


def register_component():
    return "filters", {
        "instantiation_policy": "multi",
        "instantiate_on": "demand",
        "class": FiltersComponent,
    }
