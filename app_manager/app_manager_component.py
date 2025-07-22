import app
import mainwindow
from component_registry import register_app_component


@register_app_component(
    name="app_manager", policy="singleton", instantiation_time="setup"
)
class AppManager(app.AppComponent):

    component_name = "app_manager"

    def __init__(self, app: app.App, instance_name: str):
        super().__init__(app, instance_name)

    def load_from_session(self, session):
        pass

    def save_to_session(self):
        pass

    def on_start(self):
        window = self.app.window()

        # Instantiate main components
        fields_component = self.app.instantiate_component("fields")
        filters_component = self.app.instantiate_component("filters")
        order_by_component = self.app.instantiate_component("order_by")

        # Add components to window regions
        window.add_component_to_window(fields_component, mainwindow.WindowRegion.LOWER)
        window.add_component_to_window(filters_component, mainwindow.WindowRegion.LOWER)
        window.add_component_to_window(
            order_by_component, mainwindow.WindowRegion.LOWER
        )

        # Conditional management of validation component

        if self.app.get_user_pref("validation_type", "genno") == "genno":
            validation_component = self.app.instantiate_component("validation_manager")
            window.add_component_to_window(
                validation_component, mainwindow.WindowRegion.RIGHT
            )
        if self.app.get_user_pref("validation_type", "genno") == "generic":
            generic_explorer_component = self.app.instantiate_component(
                "generic_explorer"
            )
            window.add_component_to_window(
                generic_explorer_component, mainwindow.WindowRegion.RIGHT
            )
