import json
import typing
from pathlib import Path
from typing import Union

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import mainwindow as mw
from commons import add_action_to_menu, default_prefs


class App:
    def __init__(self):
        self.main_window = mw.MainWindow(self)
        self.main_window.closing.connect(self.on_close)

        self.missing_translations = set()

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
        from fields import fields_component
        from filters import filters_component
        from query import query_component
        from query_manager import query_manager_component
        from query_view import query_view_component
        from validation_manager import validation_manager_component
        from widget_holder import widget_holder_component

        self.register_component(*datalake_component.register_component())
        self.register_component(*app_manager_component.register_component())
        self.register_component(*widget_holder_component.register_component())
        self.register_component(*validation_manager_component.register_component())
        self.register_component(*query_manager_component.register_component())
        self.register_component(*fields_component.register_component())
        self.register_component(*filters_component.register_component())
        self.register_component(*query_component.register_component())
        self.register_component(*query_view_component.register_component())

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
            print("Cannot instantiate singleton!")
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

        return new_instance

    def remove_instance(self, component_name: str, instance_name: str):
        if component_name in self.components:
            instances = self.components[component_name]["instances"]
            if instance_name in instances:
                # TODO: Call AppComponent.on_delete() - Not implemented yet
                del instances[instance_name]

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

        last_session_path: Path = self.get_last_session_path()

        if last_session_path is not None and last_session_path.is_file():
            self.load_session(last_session_path)

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

    # UTILS

    def get_config_folder(self) -> typing.Tuple[bool, typing.Union[Path | None]]:
        try:
            config_folder = Path(self.load_user_prefs()["config_folder"])
            return True, config_folder
        except KeyError:
            qw.QMessageBox.warning(
                self.window(),
                self.translate("Validation"),
                self.translate(
                    "No configuration folder defined. Aborting",
                ),
            )
            config_folder = qw.QFileDialog.getExistingDirectory(
                self.window(),
                self.translate("No configuration folder defined. Aborting"),
            )
            if config_folder:
                self.save_user_prefs({"config_folder": config_folder})
                return True, Path(config_folder)
            else:
                return False, None

    def load_user_prefs(self):
        user_prefs = self.get_user_prefs_file()
        prefs = {}
        if user_prefs.exists():
            with open(user_prefs, "r", encoding="utf-8") as f:
                prefs = json.load(f)
        else:
            prefs = default_prefs()
        return prefs

    def get_user_prefs_file(self):
        return (
            Path(
                qc.QStandardPaths().writableLocation(
                    qc.QStandardPaths.StandardLocation.AppDataLocation
                )
            )
            / "config.json"
        ).resolve()

    def save_user_prefs(self, prefs: dict):

        user_prefs = self.get_user_prefs_file()
        if not user_prefs.parent.exists():
            user_prefs.parent.mkdir(parents=True, exist_ok=True)
        old_prefs = {}
        if user_prefs.exists():
            with open(user_prefs, "r", encoding="utf-8") as f:
                old_prefs = json.load(f)

        old_prefs.update(prefs)

        with open(user_prefs, "w", encoding="utf-8") as f:
            json.dump(old_prefs, f, ensure_ascii=False)

    def get_user_prefs(self):
        pass

    # TRANSLATIONS

    def load_translations(self):
        user_prefs: dict = self.load_user_prefs()
        lang = user_prefs.get("language", "fr_FR")
        self.translations = {}
        if lang:
            from translations import TRANSLATIONS

            self.translations = TRANSLATIONS.get(lang, dict())

    def translate(self, from_str: str) -> str:
        """Translates given `from_str` to the selected language. If translation doesn't exist, this will return `from_str`

        Args:
            from_str (str): String to translate from

        Returns:
            str: Translated string
        """
        if from_str not in self.translations:
            self.missing_translations.add(from_str)
        return self.translations.get(from_str, from_str)

    def load_session(self, path: Path):
        with path.open() as f:
            session = json.load(f)
            for comp_name in session:
                for instance_name in session[comp_name]:
                    if comp_name in self.components:
                        if instance_name in self.components[comp_name]["instances"]:
                            component: AppComponent = self.components[comp_name][
                                "instances"
                            ][instance_name]
                            component.load_from_session(
                                session[comp_name][instance_name]
                            )

    def save_session(self, path: Path):
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

        session = {}
        for comp_name, comp_info in self.components.items():
            session[comp_name] = {}
            for instance_name, instance in comp_info["instances"].items():
                instance: AppComponent
                session[comp_name][instance_name] = instance.save_to_session()

        with open(path, "w") as f:
            json.dump(session, f)

    def get_last_session_path(self):
        user_prefs: dict = self.load_user_prefs()
        last_sesssion_path: str = user_prefs.get("last_session")
        if last_sesssion_path:
            return Path(last_sesssion_path)
        return None

    def on_close(self):
        # Save missing translations
        if self.missing_translations:
            with open("missing_translations.txt", "w") as f:
                for k in self.missing_translations:
                    f.write(f'"{k}":"",\n')

        last_sesssion_path = self.get_last_session_path()
        if last_sesssion_path:
            self.save_session(last_sesssion_path)


class AppComponent(qc.QObject):

    def __init__(self, app: App, instance_name: str, parent_component: "AppComponent"):
        super().__init__()

    def get_instance_name(self) -> str:
        raise NotImplementedError()

    def load_from_session(self, session: dict):
        """Load this AppComponent from `session` dict.

        Args:
            session (dict): The serialized representation of this `AppComponent` from saved session.
        """
        raise NotImplementedError()

    def save_to_session(self) -> dict:
        """Get serialized representation of this `AppComponent`

        Returns:
            dict: The serialized representation of this `AppComponent`
        """
        raise NotImplementedError()

    def on_start(self):
        """Here is the place to connect to required components. If they were instantiated on setup, they should all exist at this point"""
        raise NotImplementedError()

    def widget(self) -> Union[None, qw.QWidget]:
        """Return this component's associated widget, if applicable (i.e. WIDGET is in component_type)"""
        raise NotImplementedError()

    def get_signal(self, signal_name: str) -> Union[qc.SignalInstance, None]:
        raise NotImplementedError()

    def get_menubar_entries(self) -> list[tuple[str, qg.QAction]]:
        """Returns a list of actions that should be available from the main window's menu bar.

        Returns:
            list[tuple[str, qg.QAction]]: Each tuple of the list should be of the form `("Path/to/last/parent/menu",QAction("My action"))`. It is the responsibility of the implementer to connect the returned actions' `triggered` signals.
        """
        raise NotImplementedError()

    def get_contextmenu_entries(self, local_info: dict) -> list[tuple[str, qg.QAction]]:
        """Returns a list of actions that should be available from a context menu, that this AppComponent would be able to run.
        This method is invoked whenever `self`'s actions could be useful

        Args:
            local_info (dict): Dictionnary with all the (potentially) required information to prepare this AppComponent's actions execution

        Returns:
            list[tuple[str, qg.QAction]]: Each tuple of the list should be of the form `("Path/to/last/parent/menu",QAction("My action"))`. It is the responsibility of the implementer to connect the returned actions' signals.
        """
        raise NotImplementedError()


if __name__ == "__main__":
    import sys

    pyside_app = qw.QApplication(sys.argv)
    pyside_app.setApplicationName("cutevariant-nano")
    pyside_app.setOrganizationName("CharlesMB")

    app = App()

    sys.exit(pyside_app.exec())
