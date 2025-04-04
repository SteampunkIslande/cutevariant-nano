import app
import mainwindow
import validation_manager.validation_manager_component as validation_manager_component
import widget_holder.widget_holder_component as widget_holder


class AppManager(app.AppComponent):

    def __init__(
        self, app: app.App, instance_name: str, parent_component: app.AppComponent
    ):
        super().__init__(app, instance_name, parent_component)

    def load_from_session(self, session):
        pass

    def save_to_session(self):
        pass

    def on_start(self):
        window = self.app.window()

        # Instantiate fields selection component holder
        fields_widget_holder: widget_holder.WidgetHolderComponent = (
            self.app.instantiate_component(
                "widget_holder", "fields_widget_holder", self
            )
        )
        fields_widget_holder.set_title(self.app.translate("Fields selection"))

        # Instantiate filters selection component holder
        filters_widget_holder: widget_holder.WidgetHolderComponent = (
            self.app.instantiate_component(
                "widget_holder", "filters_widget_holder", self
            )
        )
        filters_widget_holder.set_title(self.app.translate("Filters selection"))

        # Instantiate order by selection component holder
        order_by_widget_holder: widget_holder.WidgetHolderComponent = (
            self.app.instantiate_component(
                "widget_holder", "order_by_widget_holder", self
            )
        )
        order_by_widget_holder.set_title(self.app.translate("Order by selection"))

        # Instantiate validation component itself
        validation_component: (
            validation_manager_component.ValidationManagerComponent
        ) = self.app.instantiate_singleton("validation_manager")

        window.add_component_to_window(
            fields_widget_holder, mainwindow.WindowRegion.LOWER
        )
        window.add_component_to_window(
            filters_widget_holder, mainwindow.WindowRegion.LOWER
        )
        window.add_component_to_window(
            order_by_widget_holder, mainwindow.WindowRegion.LOWER
        )

        window.add_component_to_window(
            validation_component, mainwindow.WindowRegion.RIGHT
        )

    def widget(self):
        return None

    def generic_receiver(
        self,
        action: str,
        sender_component_name: str,
        sender_instance_name: str,
        payload: dict,
    ):
        if action == "current_query_changed":
            fields_widget_holder: widget_holder.WidgetHolderComponent = (
                self.app.get_component("widget_holder", "fields_widget_holder")
            )
            filters_widget_holder: widget_holder.WidgetHolderComponent = (
                self.app.get_component("widget_holder", "filters_widget_holder")
            )
            order_by_widget_holder: widget_holder.WidgetHolderComponent = (
                self.app.get_component("widget_holder", "order_by_widget_holder")
            )

            current_query_fields_component = self.app.get_component(
                "fields", f"{payload['current_query']}/fields"
            )
            current_query_filters_component = self.app.get_component(
                "filters", f"{payload['current_query']}/filters"
            )
            current_query_order_by_component = self.app.get_component(
                "order_by", f"{payload['current_query']}/order_by"
            )
            if not all(
                [
                    fields_widget_holder,
                    filters_widget_holder,
                    order_by_widget_holder,
                    current_query_fields_component,
                    current_query_filters_component,
                    current_query_order_by_component,
                ]
            ):
                return
            fields_widget_holder.set_current_component(
                current_query_fields_component.get_instance_name()
            )
            filters_widget_holder.set_current_component(
                current_query_filters_component.get_instance_name()
            )
            order_by_widget_holder.set_current_component(
                current_query_order_by_component.get_instance_name()
            )

    def get_menubar_entries(self):
        return []

    def get_contextmenu_entries(self, local_info):
        return []


def register_component():
    return "app-manager", {
        "instantiation_policy": "singleton",
        "instantiate_on": "setup",
        "class": AppManager,
    }
