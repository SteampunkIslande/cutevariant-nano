import importlib
import json
import logging
import typing
from pathlib import Path
from typing import Union

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import mainwindow as mw
from commons import add_action_to_menubar, default_prefs
from component_registry import APP_COMPONENT_REGISTRY

LOGGER = logging.getLogger(__name__)


class App(qc.QObject):

    current_query_changed = qc.Signal()
    current_variant_changed = qc.Signal()
    current_datalake_changed = qc.Signal()

    application_started = qc.Signal()
    application_closing = qc.Signal()

    broadcast_dispatcher = qc.Signal(str, str, str, dict)

    def __init__(self):
        super().__init__()
        self.main_window = mw.MainWindow(self)
        self.main_window.closing.connect(self.on_close)

        self.app_options: dict = {}

        self.missing_translations = set()

        # Very first thing to do, translations are needed to setup menus and actions (among others)
        self.load_translations()

        self.components: dict[str, dict[str, Union[dict, AppComponent]]] = {}

        # Find and register all components
        self.register_components()

        # Instantiate components that should be instantiated on setup
        self.setup_app()

        # Allow all the instantiated components to connect to one another, now that they have been instantiated
        self.start()

    # COMPONENT REGISTRATION

    def register_components(self):
        # Chemin de base du projet
        base_path = Path(__file__).parent

        # Trouver récursivement tous les fichiers *_component.py
        component_files = []
        for path in base_path.rglob("*_component.py"):
            if path.is_file():
                component_files.append(path)

        # Importer dynamiquement chaque fichier
        for file_path in component_files:
            try:
                # Créer un nom de module basé sur le chemin
                module_name = file_path.stem
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                LOGGER.debug(f"Successfully imported component: {file_path}")
            except Exception as e:
                LOGGER.error(f"Failed to import component {file_path}: {str(e)}")

        # Enregistrer les composants depuis le registre global
        for name, component_def in APP_COMPONENT_REGISTRY.registry.items():
            self.components[name] = {
                "definition": component_def,
                "instances": {},
            }

    # COMPONENTS INSTANTIATION

    def setup_app(self):

        self.set_config_folder_action = qg.QAction(self.translate("Set config folder"))
        self.set_config_folder_action.triggered.connect(self.set_config_folder)
        add_action_to_menubar(
            self.main_window.menuBar(),
            self.translate("File"),
            self.set_config_folder_action,
        )

        if self.get_app_option("debug"):
            self.show_loaded_components_action = qg.QAction(
                self.translate("Show loaded components")
            )
            self.show_loaded_components_action.triggered.connect(
                self.show_loaded_components
            )
            add_action_to_menubar(
                self.main_window.menuBar(),
                self.translate("File/Debug"),
                self.show_loaded_components_action,
            )

            self.show_reference_tree_action = qg.QAction(
                self.translate("Show python reference tree")
            )
            self.show_reference_tree_action.triggered.connect(self.show_reference_tree)
            add_action_to_menubar(
                self.main_window.menuBar(),
                self.translate("File/Debug"),
                self.show_reference_tree_action,
            )

        for component_name, component in self.components.items():
            definition = component["definition"]
            instantiate_on = definition["instantiate_on"]
            instantiation_policy = definition["instantiation_policy"]
            if instantiate_on == "setup" and instantiation_policy == "singleton":
                self.instantiate_singleton(component_name)

        LOGGER.info(f"Registered components: {list(self.components.keys())}")

    def show_reference_tree(self):
        pass

    def get_app_option(self, option: str, default=None) -> typing.Any:
        return self.app_options.get(option, default)

    def set_app_options(self, options: dict):
        self.app_options = options

    def show_loaded_components(self):
        print("Loaded components:")
        for component_name in self.components:
            print(component_name)
            for instance_name in self.components[component_name]["instances"]:
                print(f"  - {instance_name}")

    def instantiate_singleton(self, component_name: str):
        # Vérifier si une instance existe déjà et la retourner
        if (
            component_name in self.components
            and self.components[component_name]["instances"]
        ):
            existing_instance = next(
                iter(self.components[component_name]["instances"].values())
            )
            LOGGER.debug(f"Returning existing singleton instance of {component_name}")
            return existing_instance

        LOGGER.debug(f"Creating new singleton instance for {component_name}")
        new_instance: AppComponent = self.instantiate_component(
            component_name, component_name
        )

        new_instance_menu_entries: list[tuple[str, qg.QAction]] = (
            new_instance.get_menubar_entries()
        )

        if not new_instance_menu_entries:
            LOGGER.warning(f"Component {component_name} returned no menu entries")

        # Populate the mainwindow's menubar. If there are no menu entries for this component, this does nothing
        for menu_entry in new_instance_menu_entries:
            entry_path, entry_action = menu_entry
            add_action_to_menubar(self.main_window.menuBar(), entry_path, entry_action)

        return new_instance

    def remove_instance(self, instance: "AppComponent"):

        import objgraph

        instance_name: str = instance.get_instance_name()
        component_name: str = instance.component_name
        if not instance_name or not component_name:
            LOGGER.warning(
                "Cannot remove instance, instance_name or component_name is not set!"
            )
            return

        if component_name in self.components:
            instances: dict[str, AppComponent] = self.components[component_name][
                "instances"
            ]
            if instance_name in instances:
                popped_instance = instances.pop(instance_name)
                if popped_instance is not instance:
                    LOGGER.warning(
                        f"Logical error: instance {instance_name} of component {component_name} is not the one being removed!"
                    )
                # print reference count
                LOGGER.debug(
                    " ".join(
                        [instance_name, component_name, str(sys.getrefcount(instance))]
                    )
                )
                objgraph.show_backrefs(
                    [instance],
                    filename=f"{component_name}-{instance_name}-references.png".replace(
                        "/", "_"
                    ).replace(" ", "_"),
                )
                del instance

    def instantiate_component(
        self,
        component_name: str,
        instance_name: str,
    ):
        if component_name not in self.components:
            LOGGER.warning(
                f"Cannot instantiate component <{component_name}>, component is not registered!"
            )
            return
        definition = self.components[component_name]["definition"]
        instantiation_policy = definition["instantiation_policy"]

        # For singleton policy, enforce single instance
        if instantiation_policy == "singleton":
            instance_name = component_name  # Use component name as instance name
            # Vérifier dans toutes les instances existantes
            if (
                component_name in self.components
                and instance_name in self.components[component_name]["instances"]
            ):
                existing_instance = self.components[component_name]["instances"][
                    instance_name
                ]
                LOGGER.debug(
                    f"Singleton instance found for {component_name}, returning existing instance"
                )
                return existing_instance

        instances: dict[str, AppComponent] = self.components[component_name][
            "instances"
        ]

        instance: AppComponent = definition["class"](self, instance_name)
        instance.broadcast.connect(self.dispatch_broadcast)
        self.broadcast_dispatcher.connect(instance.generic_receiver)
        self.application_closing.connect(instance.close_component)

        instances[instance_name] = instance
        LOGGER.debug(f"Instantiated {component_name} instance: {instance_name}")

        return instance

    def dispatch_broadcast(
        self,
        action: str,
        sender_component_name: str,
        sender_instance_name: str,
        payload: dict,
    ):
        self.broadcast_dispatcher.emit(
            action, sender_component_name, sender_instance_name, payload
        )

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

    def set_config_folder(self) -> typing.Tuple[bool, typing.Union[Path | None]]:
        config_folder = qw.QFileDialog.getExistingDirectory(
            self.window(),
            self.translate("Please choose a configuration folder"),
        )
        if config_folder:
            self.save_user_prefs({"config_folder": config_folder})
            return True, Path(config_folder)
        else:
            return False, None

    def get_config_folder(self) -> typing.Tuple[bool, typing.Union[Path | None]]:
        user_prefs = self.get_user_prefs()
        if "config_folder" in user_prefs:
            config_folder = Path(user_prefs["config_folder"])
            return True, config_folder
        else:
            qw.QMessageBox.warning(
                self.window(),
                self.translate("Validation"),
                self.translate(
                    "No configuration folder defined. Please choose one",
                ),
            )
            return self.set_config_folder()

    def get_user_prefs(self):
        user_prefs = self.get_user_prefs_file()
        prefs = {}
        if user_prefs.exists():
            with open(user_prefs, "r", encoding="utf-8") as f:
                prefs = json.load(f)
        else:
            prefs = default_prefs()
            self.save_user_prefs(prefs)
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
        """Saves `prefs` to the user's preferences file. This file is located in the user's writable location, in a folder named `config.json`
        It's OK to call this method with a partial dictionary, it will only update the keys that are present in the passed dictionary.
        """

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

    # TRANSLATIONS

    def load_translations(self):
        user_prefs: dict = self.get_user_prefs()
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
        user_prefs: dict = self.get_user_prefs()
        last_sesssion_path: str = user_prefs.get("last_session")
        if last_sesssion_path:
            return Path(last_sesssion_path)
        return None

    def on_close(self):

        last_sesssion_path = self.get_last_session_path()
        if self.missing_translations:
            print("Missing translations:", self.missing_translations)
        if last_sesssion_path:
            self.save_session(last_sesssion_path)

        self.application_closing.emit()


class AppComponent(qc.QObject):

    broadcast = qc.Signal(str, str, str, dict)
    closing = qc.Signal()

    component_name: str = None

    def __init__(self, app: App, instance_name: str):
        super().__init__(parent=app)
        self.app: App = app
        self.instance_name = instance_name
        self.destroyed.connect(self.on_destroy)
        # Liste pour stocker les connexions (émetteur, nom_signal_str, handler)
        self._managed_connections = []

    def get_instance_name(self) -> str:
        return self.instance_name

    def connect_signal(self, signal_emitter, signal_name_str, slot_handler):
        """Connecte un signal et enregistre la connexion pour un cleanup automatique."""
        try:
            signal = getattr(signal_emitter, signal_name_str)
            # Tenter de déconnecter d'abord pour éviter les connexions multiples du même slot
            try:
                signal.disconnect(slot_handler)
            except (
                TypeError,
                RuntimeError,
            ):  # TypeError si jamais connecté, RuntimeError si objet C++ détruit
                pass
            signal.connect(slot_handler)
            self._managed_connections.append(
                (signal_emitter, signal_name_str, slot_handler)
            )
            LOGGER.debug(
                f"Connected {signal_name_str} from {signal_emitter} to {slot_handler} for {self.instance_name}"
            )
        except AttributeError:
            LOGGER.error(
                f"Signal {signal_name_str} not found on {signal_emitter} for {self.instance_name}"
            )
        except Exception as e:
            LOGGER.error(
                f"Error connecting signal {signal_name_str} for {self.instance_name}: {e}"
            )

    def disconnect_signal(self, signal_emitter, signal_name_str, slot_handler):
        """Déconnecte un signal spécifique et le retire de la gestion si présent."""
        try:
            signal = getattr(signal_emitter, signal_name_str)
            signal.disconnect(slot_handler)
            LOGGER.debug(
                f"Disconnected {signal_name_str} from {slot_handler} for {self.instance_name}"
            )
        except (
            TypeError,
            RuntimeError,
        ):  # TypeError si pas connecté, RuntimeError si objet C++ détruit
            pass  # Pas grave si on essaie de déconnecter quelque chose qui ne l'est pas/plus
        except Exception as e:
            LOGGER.error(
                f"Error disconnecting signal {signal_name_str} for {self.instance_name}: {e}"
            )
        finally:
            # Retirer de la liste de gestion si la tentative de déconnexion a été faite
            connection_tuple = (signal_emitter, signal_name_str, slot_handler)
            if connection_tuple in self._managed_connections:
                self._managed_connections.remove(connection_tuple)

    def load_from_session(self, session: dict):
        """Load this AppComponent from `session` dict.

        Args:
            session (dict): The serialized representation of this `AppComponent` from saved session.
        """
        LOGGER.debug(f"{self.__class__.__name__} did not implement load_from_session")
        pass

    def save_to_session(self) -> dict:
        """Get serialized representation of this `AppComponent`

        Returns:
            dict: The serialized representation of this `AppComponent`
        """
        LOGGER.debug(f"{self.__class__.__name__} did not implement save_to_session")
        return {}

    def on_start(self):
        """Here is the place to connect to required components. If they were instantiated on setup, they should all exist at this point"""
        LOGGER.debug(f"{self.__class__.__name__} did not implement on_start")
        pass

    def widget(self) -> Union[None, qw.QWidget]:
        """Return this component's associated widget, if applicable (i.e. WIDGET is in component_type)"""
        LOGGER.debug(f"{self.__class__.__name__} did not implement widget")
        return None

    def get_menubar_entries(self) -> list[tuple[str, qg.QAction]]:
        """Returns a list of actions that should be available from the main window's menu bar.

        Returns:
            list[tuple[str, qg.QAction]]: Each tuple of the list should be of the form `("Path/to/last/parent/menu",QAction("My action"))`. It is the responsibility of the implementer to connect the returned actions' `triggered` signals.
        """
        LOGGER.debug(f"{self.__class__.__name__} did not implement get_menubar_entries")
        return []

    def get_contextmenu_entries(self, local_info: dict) -> list[tuple[str, qg.QAction]]:
        """Returns a list of actions that should be available from a context menu, that this AppComponent would be able to run.
        This method is invoked whenever `self`'s actions could be useful

        Args:
            local_info (dict): Dictionnary with all the (potentially) required information to prepare this AppComponent's actions execution

        Returns:
            list[tuple[str, qg.QAction]]: Each tuple of the list should be of the form `("Path/to/last/parent/menu",QAction("My action"))`. It is the responsibility of the implementer to connect the returned actions' signals.
        """
        LOGGER.debug(
            f"{self.__class__.__name__} did not implement get_contextmenu_entries"
        )
        return []

    def cleanup(self):
        """Cleanup this AppComponent. Déconnecte tous les signaux et nettoie les ressources."""
        LOGGER.debug(
            f"Base cleanup for {self.instance_name} ({self.__class__.__name__})"
        )
        # Déconnecter dans l'ordre inverse de connexion pourrait être plus sûr dans certains cas, mais simple itération ici
        for emitter, signal_name, handler in list(
            self._managed_connections
        ):  # list() pour copier car on modifie
            try:
                signal_instance = getattr(emitter, signal_name)
                signal_instance.disconnect(handler)
                LOGGER.debug(
                    f"Managed disconnect of {signal_name} from {handler} for {self.instance_name}"
                )
            except RuntimeError:
                LOGGER.warning(
                    f"Error during managed disconnect of {signal_name} for {self.instance_name}: emitter/receiver likely deleted."
                )
            except AttributeError:
                LOGGER.warning(
                    f"Error during managed disconnect of {signal_name} for {self.instance_name}: signal attribute not found (object changed?)."
                )
            except Exception as e:
                LOGGER.error(
                    f"Unexpected error during managed disconnect of {signal_name} for {self.instance_name}: {e}"
                )
        self._managed_connections.clear()
        # Les classes filles doivent appeler super().cleanup()

    def close_component(self):
        LOGGER.debug(f"Closing component {self.instance_name}...")
        self.closing.emit()  # Permet aux dépendants de se nettoyer d'abord
        self.cleanup()
        self.deleteLater()  # Crucial pour la destruction Qt

    def on_destroy(self):
        LOGGER.debug(f"Component {self.instance_name} destroyed. Removing from App.")
        if self.app:  # self.app peut être None si déjà nettoyé
            self.app.remove_instance(self)
            self.app = None  # Rompre le cycle de référence

    def generic_receiver(
        self,
        action: str,
        sender_component_name: str,
        sender_instance_name: str,
        payload: dict,
    ):
        pass


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode",
    )
    parser.add_argument(
        "--log-level",
        "-l",
        type=str,
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    pyside_app = qw.QApplication(sys.argv)

    pyside_app.setApplicationName("cutevariant-nano")
    pyside_app.setOrganizationName("CharlesMB")

    app = App()
    app.set_app_options(vars(args))

    app.main_window.show()

    sys.exit(pyside_app.exec())
