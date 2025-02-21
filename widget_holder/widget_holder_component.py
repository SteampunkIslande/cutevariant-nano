from PySide6.QtCore import SignalInstance
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget

import app


class WidgetHolderComponent(app.AppComponent):
    """Allows one widget to hold several AppComponents at the same time, only displaying one at a time. This component is not responsible for choosing, but rather the component that's using it."""

    def __init__(
        self,
        app: app.App,
        instance_name: str,
        parent_component: app.AppComponent = None,
    ):
        self.app = app
        self.instance_name = instance_name
        self.parent_component = parent_component

        self.held_components: dict[str, "app.AppComponent"] = {}
        self.current_component_name = None

    def load_from_session(self, session: dict):
        # Implement loading logic here
        pass

    def save_to_session(self) -> dict:
        # Implement saving logic here
        return {}

    def on_start(self):
        # Implement startup logic here
        pass

    def add_component(self, component: "app.AppComponent"):
        pass

    def widget(self) -> QWidget:
        if self.current_component_name is None:
            return
        current_component = self.held_components.get(self.current_component_name)
        if current_component is None:
            return
        return self.held_components.get(self.current_component_name)

    def get_signal(self, signal_name: str) -> SignalInstance:
        # Implement signal retrieval logic here
        return None

    def get_menubar_entries(self) -> list[tuple[str, QAction]]:
        # Implement menubar entries logic here
        return []

    def get_contextmenu_entries(self, local_info: dict) -> list[tuple[str, QAction]]:
        # Implement context menu entries logic here
        return []


def register_component():
    return "widget_holder", {
        "instantiation_policy": "multi",
        "instantiate_on": "demand",
        "class": WidgetHolderComponent,
    }
