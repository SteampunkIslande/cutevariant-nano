import app


class ValidationSelectionComponent(app.AppComponent):

    def __init__(
        self, app: app.App, instance_name: str, parent_component: app.AppComponent
    ):
        self.app = app
        self.instance_name = instance_name
        self.parent_componennt = parent_component

    def get_instance_name(self):
        return self.instance_name

    def load_from_session(self, session):
        return

    def save_to_session(self):
        return

    def on_start(self):
        return

    def widget(self):
        return

    def get_signal(self, signal_name):
        return

    def get_menubar_entries(self):
        return

    def get_contextmenu_entries(self, local_info):
        return


def register_component():
    return "validation_selection", {
        "instantiation_policy": "multi",
        "instantiate_on": "demand",
        "class": ValidationSelectionComponent,
    }
