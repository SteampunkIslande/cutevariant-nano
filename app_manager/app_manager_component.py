import app
import mainwindow
import validation_manager.validation_manager_component as validation_manager_component
import fields.fields_component as fld_cmp
import filters.filters_component as flt_cmp
import order_by.order_by_component as ob_cmp


class AppManager(app.AppComponent):

    def __init__(self, app: app.App, instance_name: str):
        super().__init__(app, instance_name)

    def load_from_session(self, session):
        pass

    def save_to_session(self):
        pass

    def on_start(self):
        window = self.app.window()

        fields_component: fld_cmp.FieldsComponent = self.app.instantiate_component(
            "fields", "fields"
        )
        filters_component: flt_cmp.FiltersComponent = self.app.instantiate_component(
            "filters", "filters"
        )
        order_by_component: ob_cmp.OrderByComponent = self.app.instantiate_component(
            "order_by", "order_by"
        )

        window.add_component_to_window(fields_component, mainwindow.WindowRegion.LOWER)
        window.add_component_to_window(filters_component, mainwindow.WindowRegion.LOWER)
        window.add_component_to_window(
            order_by_component, mainwindow.WindowRegion.LOWER
        )

        if self.app.get_app_option("validation", "genno") == "genno":
            # Instantiate validation component itself
            validation_component: (
                validation_manager_component.ValidationManagerComponent
            ) = self.app.instantiate_singleton("validation_manager")
            window.add_component_to_window(
                validation_component, mainwindow.WindowRegion.RIGHT
            )
        else:
            generic_explorer_component: (
                validation_manager_component.ValidationManagerComponent
            ) = self.app.instantiate_singleton("validation_manager")
            window.add_component_to_window(
                generic_explorer_component, mainwindow.WindowRegion.LEFT
            )


def register_component():
    return "app-manager", {
        "instantiation_policy": "singleton",
        "instantiate_on": "setup",
        "class": AppManager,
    }
