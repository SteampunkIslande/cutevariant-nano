from abc import ABC, ABCMeta, abstractmethod
from typing import Union

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import mainwindow as mw
from commons import add_action_to_menu, load_user_prefs


class App:
    def __init__(self):
        self.main_window = mw.MainWindow()

        # Very first thing to do, translations are needed to setup menus and actions (among others)
        self.load_translations()

        self.components: dict[str, Union[dict[str, AppComponent], dict]] = {}

        # Find and register all components
        self.register_components()

        # Instantiate components that should be instantiated on setup
        self.setup_app()

        # Allow all the instantiated components to connect to one another, now that they have been instantiated
        self.start()

        self.main_window.show()

    # COMPONENT REGISTRATION

    def register_components(self):
        # To be able to compile with nuitka, manually import all the components in the project.
        # If you'd like your own component to be included, just add it to the source folder and import it here
        from app_manager import app_manager_component
        from datalake import datalake_component

        self.register_component(*datalake_component.register_component())
        self.register_component(*app_manager_component.register_component())

    def register_component(self, component_name: str, component_definition: dict):
        self.components[component_name] = {
            "definition": component_definition,
            "instances": {},
        }

    # COMPONENTS INSTANTIATION

    def setup_app(self):
        for component_name, component in self.components.items():
            definition = component["definition"]
            instantiate_on = definition["instantiate_on"]
            instantiation_policy = definition["instantiation_policy"]
            if instantiate_on == "setup":
                if instantiation_policy == "singleton":
                    self.instantiate_singleton(component_name)

    def instantiate_singleton(self, component_name: str):
        if component_name not in self.components:
            return
        if len(self.components[component_name]["instances"]) != 0:
            return

        new_instance: AppComponent = self.instantiate_component(
            component_name, component_name
        )

        new_instance_menu_entries: list[tuple[str, qg.QAction]] = (
            new_instance.get_menubar_entries()
        )

        # Populate the mainwindow's menubar. If there are no menu entries for this component, this does nothing
        for menu_entry in new_instance_menu_entries:
            entry_path, entry_action = menu_entry
            add_action_to_menu(self.main_window.menuBar(), entry_path, entry_action)

        self.components[component_name][component_name] = new_instance

    def instantiate_component(
        self,
        component_name: str,
        instance_name: str,
        parent_component: "AppComponent" = None,
    ):
        if component_name not in self.components:
            # TODO: Maybe this should raise?
            return
        definition = self.components[component_name]["definition"]

        instances: dict[int, AppComponent] = self.components[component_name][
            "instances"
        ]
        if definition["instantiation_policy"] == "singleton":
            if len(instances) == 1:
                # Dirty way to ensure a singleton. TODO: when debugging will be implemented, this should be notified
                return

        new_instance: AppComponent = definition["class"](
            self, instance_name, parent_component
        )
        instances[instance_name] = new_instance

        return new_instance

    # APP START

    def start(self):
        for component_name in self.components:
            for _, instance in self.components[component_name]["instances"].items():
                instance: AppComponent
                instance.on_start()

    # RUNNING APP LIFE CYCLE

    def get_component(
        self, component_name: str, instance_name: str = None
    ) -> Union["AppComponent", None]:
        if component_name not in self.components:
            return

        # If we don't specify instance name, then this means it's a singleton
        instance_name = instance_name or component_name

        return self.components[component_name]["instances"].get(instance_name)

    def window(self):
        return self.main_window

    # TRANSLATIONS

    def load_translations(self):
        user_prefs: dict = load_user_prefs()
        lang = user_prefs.get("language")
        self.translations = {}
        if lang:
            from translations import TRANSLATIONS

            self.translations = TRANSLATIONS.get(lang)

    def translate(self, from_str: str) -> str:
        """Translates given `from_str` to the selected language. If translation doesn't exist, this will return `from_str`

        Args:
            from_str (str): String to translate from

        Returns:
            str: Translated string
        """
        return self.translations.get(from_str, from_str)


QObjectMeta = type(qc.QObject)


class _ABCQObjectMeta(QObjectMeta, ABCMeta):
    pass


class AppComponent(qc.QObject, ABC, metaclass=_ABCQObjectMeta):

    @abstractmethod
    def __init__(self, app: App, instance_name: str, parent_component: "AppComponent"):
        pass

    @abstractmethod
    def load_from_session(self, session: dict):
        """Load this AppComponent from `session` dict.

        Args:
            session (dict): The serialized representation of this `AppComponent` from saved session.
        """
        pass

    @abstractmethod
    def save_to_session(self) -> dict:
        """Get serialized representation of this `AppComponent`

        Returns:
            dict: The serialized representation of this `AppComponent`
        """
        pass

    @abstractmethod
    def on_start(self):
        """Here is the place to connect to required components. If they were instantiated on setup, they should all exist at this point"""
        pass

    @abstractmethod
    def widget(self) -> Union[None, qw.QWidget]:
        """Return this component's associated widget, if applicable (i.e. WIDGET is in component_type)"""
        pass

    @abstractmethod
    def get_signal(self, signal_name: str) -> Union[qc.SignalInstance, None]:
        pass

    @abstractmethod
    def get_menubar_entries(self) -> list[tuple[str, qg.QAction]]:
        """Returns a list of actions that should be available from the main window's menu bar.

        Returns:
            list[tuple[str, qg.QAction]]: Each tuple of the list should be of the form `("Path/to/last/parent/menu",QAction("My action"))`. It is the responsibility of the implementer to connect the returned actions' `triggered` signals.
        """
        pass

    @abstractmethod
    def get_contextmenu_entries(self, local_info: dict) -> list[tuple[str, qg.QAction]]:
        """Returns a list of actions that should be available from a context menu, that this AppComponent would be able to run.
        This method is invoked whenever `self`'s actions could be useful

        Args:
            local_info (dict): Dictionnary with all the (potentially) required information to prepare this AppComponent's actions execution

        Returns:
            list[tuple[str, qg.QAction]]: Each tuple of the list should be of the form `("Path/to/last/parent/menu",QAction("My action"))`. It is the responsibility of the implementer to connect the returned actions' signals.
        """
        pass


if __name__ == "__main__":
    import sys

    pyside_app = qw.QApplication(sys.argv)

    app = App()

    sys.exit(pyside_app.exec())
