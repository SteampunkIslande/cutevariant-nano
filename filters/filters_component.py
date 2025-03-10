import app
import filters.filters_widget as fltw
import query.query_component as q


class FiltersComponent(app.AppComponent):

    def __init__(
        self, app: app.App, instance_name: str, parent_component: "q.QueryComponent"
    ):
        super().__init__(app, instance_name, parent_component)

        self.filters_widget = fltw.FiltersWidget(self.parent_component)

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


def register_component():
    return "filters", {
        "instantiation_policy": "multi",
        "instantiate_on": "demand",
        "class": FiltersComponent,
    }
