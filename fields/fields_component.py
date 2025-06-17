import logging

# Import différé pour résoudre la dépendance circulaire
from typing import TYPE_CHECKING

import app
from fields import fields_model as fldm

if TYPE_CHECKING:
    from fields.fields_widget import FieldsWidget

from component_registry import register_app_component

LOGGER = logging.getLogger(__name__)


@register_app_component(name="fields", policy="multi", instantiation_time="demand")
class FieldsComponent(app.AppComponent):

    component_name = "fields"

    def __init__(self, app: app.App, instance_name: str):
        super().__init__(app, instance_name)

        self.model = fldm.FieldsModel(self)
        self.model.dataChanged.connect(self.emit_fields_changed)

        # Import local différé
        from fields.fields_widget import FieldsWidget

        self.fields_widget = FieldsWidget(self.app, self)
        self.fields_widget.setWindowTitle(self.app.translate("Fields selection"))

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

    def cleanup(self):
        self.model = None
        self.fields_widget = None

    def __del__(self):
        print("FieldsComponent deleted")
