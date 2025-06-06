import app
import mainwindow
from component_registry import register_app_component


@register_app_component(
    name="app-manager", policy="singleton", instantiation_time="setup"
)
class AppManager(app.AppComponent):

    def __init__(self, app: app.App, instance_name: str):
        super().__init__(app, instance_name)

    def load_from_session(self, session):
        pass

    def save_to_session(self):
        pass

    def on_start(self):
        window = self.app.window()

        # Instancier les composants principaux
        fields_component = self.app.instantiate_singleton("fields")
        filters_component = self.app.instantiate_singleton("filters")
        order_by_component = self.app.instantiate_singleton("order_by")
        query_manager_component = self.app.instantiate_singleton("query_manager")

        # Ajouter les composants aux régions de la fenêtre
        window.add_component_to_window(fields_component, mainwindow.WindowRegion.LOWER)
        window.add_component_to_window(filters_component, mainwindow.WindowRegion.LOWER)
        window.add_component_to_window(
            order_by_component, mainwindow.WindowRegion.LOWER
        )
        window.add_component_to_window(
            query_manager_component, mainwindow.WindowRegion.UPPER
        )

        # Gestion conditionnelle du composant de validation
        validation_component = self.app.instantiate_singleton("validation_manager")
        if self.app.get_app_option("validation", "genno") == "genno":
            window.add_component_to_window(
                validation_component, mainwindow.WindowRegion.RIGHT
            )
        else:
            window.add_component_to_window(
                validation_component, mainwindow.WindowRegion.LEFT
            )

    def cleanup(self):
        # Clean up resources
        # AppManager ne contient pas de ressources spécifiques à nettoyer
        # Appeler le cleanup du parent
        super().cleanup()
