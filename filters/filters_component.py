import app
import filters.filters_model as fltm
import filters.filters_widget as fltw
import query.query_component as q


class FiltersComponent(app.AppComponent):

    def __init__(
        self, app: app.App, instance_name: str, parent_component: "q.QueryComponent"
    ):
        super().__init__(app, instance_name, parent_component)

        self.model = fltm.FilterModel(self)
        self.model.load(
            {
                "filter_type": "ROOT",
                "children": [{"filter_type": "AND", "children": []}],
            }
        )
        self.model.model_changed.connect(self.emit_filters_changed)

        self.filters_widget = fltw.FiltersWidget(self.app, self, self.model)

    def get_instance_name(self):
        return self.instance_name

    def load_from_session(self, session):
        return

    def save_to_session(self):
        return

    def on_start(self):
        return

    def widget(self):
        return self.filters_widget

    def get_signal(self, signal_name):
        return

    def get_menubar_entries(self):
        return

    def get_contextmenu_entries(self, local_info):
        return

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
        if sender_component_name + "/filters" == self.instance_name:
            if action == "query:all_fields_changed":
                self.model.load(
                    {
                        "filter_type": "ROOT",
                        "children": [{"filter_type": "AND", "children": []}],
                    }
                )

    def __del__(self):
        print("FiltersComponent deleted")


def register_component():
    return "filters", {
        "instantiation_policy": "multi",
        "instantiate_on": "demand",
        "class": FiltersComponent,
    }
