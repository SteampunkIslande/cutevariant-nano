import app
from fields import fields_model as fldm
from fields.fields_widget import FieldsWidget


class FieldsComponent(app.AppComponent):

    def __init__(
        self, app: app.App, instance_name: str, parent_component: app.AppComponent
    ):
        super().__init__(app, instance_name, parent_component)

        self.model = fldm.FieldsModel(self)
        self.model.dataChanged.connect(self.emit_fields_changed)

        self.fields_widget = FieldsWidget(self.app, self.model)

    def get_instance_name(self):
        return self.instance_name

    def load_from_session(self, session):
        return

    def save_to_session(self):
        return

    def on_start(self):
        return

    def widget(self):
        return self.fields_widget

    def get_signal(self, signal_name):
        return

    def get_menubar_entries(self):
        return

    def get_contextmenu_entries(self, local_info):
        return

    def emit_fields_changed(self):
        self.broadcast.emit(
            "selected_fields_changed",
            "fields",
            self.instance_name,
            {"fields": self.model.checked_fields()},
        )

    def generic_receiver(
        self,
        action: str,
        sender_component_name: str,
        sender_instance_name: str,
        payload: dict,
    ):
        if action == "query_fields_changed":
            # We are concerned
            if payload["current_query"] == self.parent_component.get_instance_name():
                self.update_fields(payload["fields"])
        return

    def update_fields(self, fields: list[str]):
        self.model.update_fields(fields)


def register_component():
    return "fields", {
        "instantiation_policy": "multi",
        "instantiate_on": "demand",
        "class": FieldsComponent,
    }
