import app
import datalake
import datalake.datalake_component as datalake
import mainwindow
import validation_manager.validation_manager_component as validation_manager_component
import widget_holder.widget_holder_component as widget_holder


class AppManager(app.AppComponent):

    def __init__(
        self, app: app.App, instance_name: str, parent_component: app.AppComponent
    ):
        super().__init__(app, instance_name, parent_component)

        self.datalake = None
        self.variant_info_holder = None
        self.genotype_info_holder = None
        self.fields_widget_holder = None
        self.filters_widget_holder = None
        self.validation_component = None

        self.main_window = None

    def get_instance_name(self):
        return self.instance_name

    def load_from_session(self, session):
        pass

    def save_to_session(self):
        pass

    def on_start(self):
        self.datalake: datalake.Datalake = self.app.get_component("datalake")

        # Instantiate appropriate components for variant validation

        # Instantiate variant info component holder -> TODO: Should be a singleton
        self.variant_info_holder: widget_holder.WidgetHolderComponent = (
            self.app.instantiate_component("widget_holder", "variant_info_holder", self)
        )
        self.variant_info_holder.set_title(self.app.translate("Variant info"))

        # Instantiate genotype info component holder -> TODO: Should be a singleton
        self.genotype_info_holder: widget_holder.WidgetHolderComponent = (
            self.app.instantiate_component(
                "widget_holder", "genotype_info_holder", self
            )
        )
        self.genotype_info_holder.set_title(self.app.translate("Genotype info"))

        # Instantiate fields selection component holder
        self.fields_widget_holder: widget_holder.WidgetHolderComponent = (
            self.app.instantiate_component(
                "widget_holder", "fields_widget_holder", self
            )
        )
        self.fields_widget_holder.set_title(self.app.translate("Fields selection"))

        # Instantiate filters selection component holder
        self.filters_widget_holder: widget_holder.WidgetHolderComponent = (
            self.app.instantiate_component(
                "widget_holder", "filters_widget_holder", self
            )
        )
        self.filters_widget_holder.set_title(self.app.translate("Filters selection"))

        # Instantiate validation component itself
        self.validation_component: (
            validation_manager_component.ValidationManagerComponent
        ) = self.app.instantiate_singleton("validation_manager")

        self.main_window = self.app.window()

        self.main_window.add_component_to_window(
            self.variant_info_holder, mainwindow.WindowRegion.LEFT
        )
        self.main_window.add_component_to_window(
            self.genotype_info_holder, mainwindow.WindowRegion.LEFT
        )
        self.main_window.add_component_to_window(
            self.fields_widget_holder, mainwindow.WindowRegion.LOWER
        )
        self.main_window.add_component_to_window(
            self.filters_widget_holder, mainwindow.WindowRegion.LOWER
        )
        self.main_window.add_component_to_window(
            self.validation_component, mainwindow.WindowRegion.RIGHT
        )

    def widget(self):
        return None

    def get_signal(self, signal_name):
        return

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
