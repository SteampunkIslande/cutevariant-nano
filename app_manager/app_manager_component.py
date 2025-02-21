import app
import datalake
import datalake.datalake_component as datalake
import widget_holder.widget_holder_component as widget_holder


class AppManager(app.AppComponent):

    def __init__(
        self, app: app.App, instance_name: str, parent_component: app.AppComponent
    ):
        self.app = app
        self.instance_name = instance_name
        self.parent_component = parent_component

        self.datalake = None
        self.variant_info_holder = None
        self.genotype_info_holder = None
        self.fields_widget_holder = None
        self.filters_widget_holder = None

    def on_start(self):
        self.datalake: datalake.Datalake = self.app.get_component("datalake")

        self.variant_info_holder: widget_holder.WidgetHolderComponent = (
            self.app.instantiate_component("widget_holder", "variant_info_holder", self)
        )

        self.genotype_info_holder: widget_holder.WidgetHolderComponent = (
            self.app.instantiate_component(
                "widget_holder", "genotype_info_holder", self
            )
        )

        self.fields_widget_holder: widget_holder.WidgetHolderComponent = (
            self.app.instantiate_component(
                "widget_holder", "fields_widget_holder", self
            )
        )

        self.filters_widget_holder: widget_holder.WidgetHolderComponent = (
            self.app.instantiate_component(
                "widget_holder", "filters_widget_holder", self
            )
        )


def register_component():
    return "app-manager", {
        "instantiation_policy": "singleton",
        "instantiate_on": "setup",
        "class": AppManager,
    }
