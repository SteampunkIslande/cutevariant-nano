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
        query_manager_component = self.app.instantiate_component("query_manager")

        # Add components to window regions
        window.add_component_to_window(fields_component, mainwindow.WindowRegion.LOWER)
        window.add_component_to_window(filters_component, mainwindow.WindowRegion.LOWER)
        window.add_component_to_window(
            order_by_component, mainwindow.WindowRegion.LOWER
        )
        window.add_component_to_window(
            query_manager_component, mainwindow.WindowRegion.UPPER
        )

        # Conditional management of validation component

        if self.app.get_app_option("validation", "genno") == "genno":
            validation_component = self.app.instantiate_component("validation_manager")
            window.add_component_to_window(
                validation_component, mainwindow.WindowRegion.RIGHT
            )
        else:
            # window.add_component_to_window(
            #     validation_component, mainwindow.WindowRegion.LEFT
            # )
            pass
