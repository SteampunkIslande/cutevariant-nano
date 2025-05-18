import app
from fields import fields_model as fldm
from fields.fields_widget import FieldsWidget
import logging

LOGGER = logging.getLogger(__name__)


class FieldsComponent(app.AppComponent):

    def __init__(self, app: app.App, instance_name: str):
        super().__init__(app, instance_name)

        self.model = fldm.FieldsModel(self)
        self.model.dataChanged.connect(self.emit_fields_changed)

        self.fields_widget = FieldsWidget(self.app, self)

    def widget(self):
        return self.fields_widget

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
        pass

    def update_fields(self, fields: list[str]):
        self.model.update_fields(fields)

    def close(self):
        self.model.close()
        self.fields_widget.close()
        self.model = None
        self.fields_widget = None
        super().close()

    def __del__(self):
        print("FieldsComponent deleted")


def register_component():
    return "fields", {
        "instantiation_policy": "multi",
        "instantiate_on": "demand",
        "class": FieldsComponent,
    }
