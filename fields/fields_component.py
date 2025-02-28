from fields_widget import FieldsWidget

import app
import query.query_component as q


class FieldsComponent(app.AppComponent):

    def __init__(
        self, app: app.App, instance_name: str, parent_component: app.AppComponent
    ):
        super().__init__(app, instance_name, parent_component)
        self.app = app
        self.instance_name = instance_name
        self.parent_component: q.QueryComponent = parent_component

        self.fields_widget = FieldsWidget(self.parent_component)

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
