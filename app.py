import json
import logging
import typing
import weakref
from formatter import Formatter
from pathlib import Path
from typing import Union

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import mainwindow as mw
from commons import add_action_to_menubar, default_prefs
from component_registry import APP_COMPONENT_REGISTRY
from formatters.nice import NiceFormatter

LOGGER = logging.getLogger(__name__)


class App(qc.QObject):

    current_query_changed = qc.Signal()
    current_variant_changed = qc.Signal()
    current_datalake_changed = qc.Signal()

    current_formatter_changed = qc.Signal(str)

    application_started = qc.Signal()
    application_closing = qc.Signal()

    broadcast_dispatcher = qc.Signal(str, str, str, dict)

    def __init__(self, app_options: dict = None):
        super().__init__()
        self.main_window = mw.MainWindow(self)
        self.main_window.closing.connect(self.on_close)

        self.formatters = {}

        self.app_options: dict = app_options or {}

        self.missing_translations = set()

        # Very first thing to do, translations are needed to setup menus and actions (among others)
        self.load_translations()

        # Automatic loading and registration of components
        self.load_component_modules()

        # Verify that components are properly registered
        if APP_COMPONENT_REGISTRY.get_component_count() == 0:
            LOGGER.warning("No components registered")

        # Instantiate components that should be instantiated on setup
        self.setup_app()

        # Allow all the instantiated components to connect to one another, now that they have been instantiated
        self.start()

    # COMPONENT REGISTRATION

    def load_component_modules(self):
        """
        Load all component modules explicitly.
        Nuitka compatible as it uses static imports.
        """
        # Explicit list for Nuitka compatibility
        # By importing these modules, we ensure they are registered in the global component registry
        import app_manager.app_manager_component
        import datalake.datalake_component
        import fields.fields_component
        import filters.filters_component
        import order_by.order_by_component
        import query.query_component
        import query_manager.query_manager_component
        import validation_manager.validation_manager_component

        component_count = APP_COMPONENT_REGISTRY.get_component_count()
        LOGGER.info(
            f"Component modules loaded: {component_count} components registered"
        )

        # Validate that all expected modules are properly loaded
        expected_components = {
            "app_manager",
            "datalake",
            "fields",
            "filters",
            "order_by",
            "query",
            "query_manager",
            "validation_manager",
        }

        registered_components = set(APP_COMPONENT_REGISTRY.get_all_components().keys())
        missing_components = expected_components - registered_components

        if missing_components:
            LOGGER.warning(
                f"Expected but unregistered components: {missing_components}"
            )

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
            LOGGER.info(
                "Debug mode enabled. Registering debug actions in the main window."
            )
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

        # Automatic instantiation of "setup" components
        all_components = APP_COMPONENT_REGISTRY.get_all_components()
        for component_name, component_data in all_components.items():
            definition = component_data["definition"]
            instantiate_on = definition["instantiate_on"]
            instantiation_policy = definition["instantiation_policy"]
            if instantiate_on == "setup" and instantiation_policy == "singleton":
                instance = self.instantiate_component(component_name)

        self.formatters = {
            "nice": NiceFormatter(self),
        }

        LOGGER.info(
            f"Setup completed: {APP_COMPONENT_REGISTRY.get_component_count()} components registered"
        )

    def setup_formatter(self):
        import ficon

        ficon.setFontPath("assets/materialdesignicons-webfont.ttf")

        self.set_current_formatter("nice")

    def get_formatter(self) -> "Formatter":
        return self.formatters.get(self.current_formatter, self.formatters["nice"])

    def set_current_formatter(self, formatter_name: str):
        self.current_formatter = formatter_name
        self.current_formatter_changed.emit(formatter_name)

    def _setup_component_menu(self, instance: "AppComponent"):
        """Configure menu entries for a component."""
        new_instance_menu_entries: list[tuple[str, qg.QAction]] = (
            instance.get_menubar_entries()
        )

        if not new_instance_menu_entries:
            LOGGER.debug(
                f"Component {instance.component_name} returned no menu entries"
            )

        # Populate the mainwindow's menubar
        for menu_entry in new_instance_menu_entries:
            entry_path, entry_action = menu_entry
            add_action_to_menubar(self.main_window.menuBar(), entry_path, entry_action)

    def show_reference_tree(self):
        """Generate a DOT file showing the reference tree from self (App)."""
        dot_content = []
        dot_content.append("digraph reference_tree {")
        dot_content.append("    splines=false;")
        dot_content.append("    rankdir=LR;")
        dot_content.append("    node [shape=box];")

        # Keep track of added nodes to avoid duplicates in DOT
        added_nodes = set()
        # Keep track of added edges to avoid duplicates
        added_edges = set()

        def is_weak_reference(obj):
            """Check if obj is a weak reference."""
            return isinstance(
                obj, (weakref.ref, weakref.ProxyType, weakref.CallableProxyType)
            )

        def should_skip_member(name, value):
            """Determine if a member should be ignored."""
            # Ignore methods, dunders, and certain built-in types
            if name.startswith("__") and name.endswith("__"):
                return True
            if callable(value) and not hasattr(value, "__dict__"):
                return True
            if isinstance(value, (type, type(None), bool, int, float, str, bytes)):
                return True
            return False

        def get_safe_node_name(name: str):
            """Return a safe node name for DOT."""
            return (
                name.replace("-", "_")
                .replace(" ", "_")
                .replace("/", "_")
                .replace("[", "_")
                .replace("]", "_")
                .replace("(", "_")
                .replace(")", "_")
                .replace('"', "")
                .replace("'", "")
                .replace(".", "_")
                .replace("*", "_")
                .replace("?", "")
            )

        def explore_object(
            obj,
            obj_name,
            parent_name=None,
            is_weak=False,
            current_path=None,
        ):
            """Recursively explore an object and add its references to the DOT graph.

            Args:
                obj: The object to explore
                obj_name: The name to give to the node
                parent_name: The parent's name (for the edge)
                is_weak: True if the reference is weak
                current_path: Set of object IDs in the current recursion path
            """
            if current_path is None:
                current_path = set()

            obj_id = id(obj)
            safe_obj_name = get_safe_node_name(obj_name)
            no_quote_obj_name = obj_name.replace('"', "")

            # Avoid cycles in the current recursion path
            if obj_id in current_path:
                # Create a node for the cycle if not already done
                if safe_obj_name not in added_nodes:
                    dot_content.append(
                        f'    {safe_obj_name}_{obj_id} [label="{no_quote_obj_name} (cycle)", style=filled, fillcolor=yellow];'
                    )
                    added_nodes.add(safe_obj_name)

                # Add the edge to the cycle if necessary
                if parent_name:
                    safe_parent_name = get_safe_node_name(parent_name)
                    line_style = "dotted" if is_weak else "solid"
                    edge_key = (safe_parent_name, safe_obj_name, line_style)
                    if edge_key not in added_edges:
                        dot_content.append(
                            f"    {safe_parent_name} -> {safe_obj_name} [style={line_style}, color=red];"
                        )
                        added_edges.add(edge_key)
                return

            # Add the object to the current recursion path
            new_path = current_path | {obj_id}

            # Add the node if it doesn't exist yet
            if safe_obj_name not in added_nodes:
                dot_content.append(
                    f'    {safe_obj_name} [label="{no_quote_obj_name}"];'
                )
                added_nodes.add(safe_obj_name)

            # Add the edge from the parent if necessary
            if parent_name:
                safe_parent_name = get_safe_node_name(parent_name)
                line_style = "dotted" if is_weak else "solid"
                edge_key = (safe_parent_name, safe_obj_name, line_style)
                if edge_key not in added_edges:
                    dot_content.append(
                        f"    {safe_parent_name} -> {safe_obj_name} [style={line_style}];"
                    )
                    added_edges.add(edge_key)

            # Explore the object's members
            if hasattr(obj, "__dict__"):
                for attr_name, attr_value in obj.__dict__.items():
                    if should_skip_member(attr_name, attr_value):
                        continue

                    # Check if it's a weak reference
                    attr_is_weak = is_weak_reference(attr_value)

                    # If it's a weak reference, try to dereference it
                    if attr_is_weak:
                        try:
                            if isinstance(attr_value, weakref.ref):
                                dereferenced = attr_value()
                                if dereferenced is not None:
                                    explore_object(
                                        dereferenced,
                                        attr_name,
                                        obj_name,
                                        True,
                                        new_path,
                                    )
                            # For other types of weak references, treat them as normal references
                            # but mark the connection as weak
                            else:
                                explore_object(
                                    attr_value,
                                    attr_name,
                                    obj_name,
                                    True,
                                    new_path,
                                )
                        except (ReferenceError, TypeError):
                            # The weak reference is dead or inaccessible
                            continue
                    else:
                        # Normal strong reference
                        explore_object(attr_value, attr_name, obj_name, False, new_path)

            # Explore elements if it's a container
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if should_skip_member(str(key), value):
                        continue
                    key_name = f"{obj_name}[{key}]"
                    explore_object(
                        value,
                        key_name,
                        obj_name,
                        is_weak_reference(value),
                        new_path,
                    )

            elif isinstance(obj, (list, tuple, set)):
                for i, value in enumerate(obj):
                    if should_skip_member(f"item_{i}", value):
                        continue
                    item_name = f"{obj_name}[{i}]"
                    explore_object(
                        value,
                        item_name,
                        obj_name,
                        is_weak_reference(value),
                        new_path,
                    )

        # Start exploration from self (App)
        # explore_object(self, "app")
        explore_object(APP_COMPONENT_REGISTRY, "APP_COMPONENT_REGISTRY")

        dot_content.append("}")

        # Write the DOT file
        dot_file_path = Path("reference_tree.dot")
        try:
            with open(dot_file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(dot_content))

            LOGGER.info(f"Reference tree generated in {dot_file_path}")

            # Display a message to the user
            qw.QMessageBox.information(
                self.window(),
                self.translate("Reference Tree Generated"),
                self.translate(
                    "Reference tree has been generated in {dot_file_path}<br><br>"
                    "You can visualize it using:<br>"
                    "<code>dot -Tpng {dot_file_path} -o reference_tree.png</code><br>"
                    "or<br>"
                    "<code>dot -Tsvg {dot_file_path} -o reference_tree.svg</code><br>"
                    "A window will open in your default browser with the visualization.".format(
                        dot_file_path=dot_file_path.name
                    )
                ),
            )

            from urllib.parse import quote

            qg.QDesktopServices.openUrl(
                "https://dreampuf.github.io/GraphvizOnline/?engine=dot#"
                + quote("\n".join(dot_content))
            )

        except Exception as e:
            LOGGER.error(f"Error generating DOT file: {e}")
            qw.QMessageBox.critical(
                self.window(),
                self.translate("Error"),
                self.translate(
                    "Error generating reference tree:\n{e}".format(e=str(e))
                ),
            )

    def get_app_option(self, option: str, default=None) -> typing.Any:
        return self.app_options.get(option, default)

    def show_loaded_components(self):
        print("Loaded components:")
        all_components = APP_COMPONENT_REGISTRY.get_all_components()
        for component_name in all_components:
            print(component_name)
            for instance_name in all_components[component_name]["instances"]:
                print(f"  - {instance_name}")

    def remove_instance(self, instance: "AppComponent"):
        """
        Remove a component instance from the registry.

        This method is now robust and works independently of Qt's destroyed signal.
        It can be called explicitly during component shutdown.

        Args:
            instance: The AppComponent instance to remove
        """
        if not instance:
            LOGGER.warning("Cannot remove None instance")
            return False

        instance_name: str = instance.get_instance_name()
        component_name: str = instance.component_name

        if not instance_name or not component_name:
            LOGGER.warning(
                f"Cannot remove instance, instance_name ({instance_name}) or component_name ({component_name}) is not set!"
            )
            return False

        component_data = APP_COMPONENT_REGISTRY.get_component_data(component_name)
        if not component_data:
            LOGGER.warning(
                f"Component {component_name} not found in registry, cannot remove instance {instance_name}"
            )
            return False

        instances: dict[str, "AppComponent"] = component_data["instances"]
        if instance_name not in instances:
            LOGGER.debug(
                f"Instance {instance_name} of component {component_name} already removed from registry"
            )
            return True  # Already removed, consider it success

        stored_instance = instances.pop(instance_name)
        if stored_instance is not instance:
            LOGGER.warning(
                f"Logical error: instance {instance_name} of component {component_name} "
                f"is not the one being removed! Registry may be corrupted."
            )

        LOGGER.info(
            f"Successfully removed instance {instance_name} from component {component_name}"
        )
        return True

    def instantiate_component(
        self,
        component_name: str,
        instance_name: str = None,
    ) -> "AppComponent":
        """
        Instantiate a component according to its defined policy.

        Args:
            component_name: Name of the component to instantiate
            instance_name: Instance name (optional for singletons)

        Returns:
            AppComponent: Created or existing instance
        """
        if not APP_COMPONENT_REGISTRY.is_component_registered(component_name):
            LOGGER.error(
                f"Component '{component_name}' not registered in the global registry"
            )
            return None

        component_data = APP_COMPONENT_REGISTRY.get_component_data(component_name)
        if not component_data:
            LOGGER.error(f"Component '{component_name}' missing from registry")
            return None
        definition = component_data["definition"]
        instances = component_data["instances"]
        policy = definition["instantiation_policy"]

        # Policy management
        if policy == "singleton":
            instance_name = component_name  # Fixed name for singletons
            if instance_name in instances:
                LOGGER.debug(f"Returning existing singleton instance: {component_name}")
                return instances[instance_name]

        elif policy == "multi":
            if not instance_name:
                raise ValueError(
                    f"Instance name required for multi component '{component_name}'"
                )
            if instance_name in instances:
                LOGGER.debug(f"Returning existing instance: {instance_name}")
                return instances[instance_name]

        # Create the new instance
        component_class = definition["class"]

        # Actual instantiation
        instance: "AppComponent" = component_class(
            self, instance_name or component_name
        )

        self._setup_component_menu(instance)

        # Automatic connections
        instance.broadcast.connect(self.dispatch_broadcast)
        self.broadcast_dispatcher.connect(instance.generic_receiver)

        self.application_closing.connect(instance.close_component)

        # Registration
        instances[instance_name or component_name] = instance
        LOGGER.info(
            f"Instance created: {component_name}/{instance_name or component_name}"
        )

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
        all_components = APP_COMPONENT_REGISTRY.get_all_components()
        for component_name in all_components:
            for _, instance in all_components[component_name]["instances"].items():
                instance: AppComponent
                instance.on_start()

        last_session_path: Path = self.get_last_session_path()

        if last_session_path is not None and last_session_path.is_file():
            self.load_session(last_session_path)

        self.setup_formatter()

    # RUNNING APP LIFE CYCLE

    def get_component(
        self, component_name: str, instance_name: str = None
    ) -> Union["AppComponent", None]:
        component_data = APP_COMPONENT_REGISTRY.get_component_data(component_name)
        if not component_data:
            return None

        # If we don't specify instance name, then this means it's a singleton
        instance_name = instance_name or component_name

        return component_data["instances"].get(instance_name)

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
                    component_data = APP_COMPONENT_REGISTRY.get_component_data(
                        comp_name
                    )
                    if component_data:
                        if instance_name in component_data["instances"]:
                            component: AppComponent = component_data["instances"][
                                instance_name
                            ]
                            component.load_from_session(
                                session[comp_name][instance_name]
                            )

    def save_session(self, path: Path):
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

        session = {}
        all_components = APP_COMPONENT_REGISTRY.get_all_components()
        for comp_name, comp_info in all_components.items():
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
        LOGGER.info("Application closing, starting cleanup process...")

        last_sesssion_path = self.get_last_session_path()
        if self.missing_translations:
            print("Missing translations:", self.missing_translations)
        if last_sesssion_path:
            self.save_session(last_sesssion_path)

        # Emit application closing signal first
        self.application_closing.emit()


class AppComponent(qc.QObject):

    broadcast = qc.Signal(str, str, str, dict)
    closing = qc.Signal()

    component_name: str = None

    def __init__(self, app: App, instance_name: str):
        super().__init__(parent=app)
        self.app: App = app
        self.instance_name = instance_name

    def get_instance_name(self) -> str:
        return self.instance_name

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
        """Cleanup this AppComponent. Disconnect all signals and clean up resources."""
        LOGGER.debug(
            f"Base cleanup for {self.instance_name} ({self.__class__.__name__})"
        )

    def close_component(self):

        LOGGER.debug(f"Closing component {self.instance_name}...")

        self.closing.emit()  # Allow dependents to clean up first

        # Explicitly remove from registry before Qt cleanup
        if self.app:
            self.app.remove_instance(self)

        self.cleanup()

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

    app = App(app_options=vars(args))

    app.main_window.show()

    sys.exit(pyside_app.exec())
