from PySide6.QtCore import SignalInstance
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

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

        self._layout_widget = QWidget()
        self._layout = QVBoxLayout()

        self._layout_widget.setLayout(self._layout)

        self.place_holder = QLabel(f"Instance::{instance_name}")
        self.place_holder.setWindowTitle(instance_name)
        self._layout.addWidget(self.place_holder)

    def get_instance_name(self):
        return self.instance_name

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

        component_name = component.get_instance_name()

        if component_name in self.held_components:
            # Maybe should raise?
            return False
        self.held_components[component_name] = component
        if self.held_components.get(self.current_component_name, None) is None:
            self.current_component_name = component_name

        for name, comp in self.held_components.items():
            if name != component_name:
                if comp.widget():
                    comp.widget().hide()
                    self._layout.removeWidget(comp.widget())
            else:
                if comp.widget():
                    self._layout.addWidget(comp.widget())

    def widget(self) -> QWidget:
        if self.current_component_name is None:
            return self.place_holder
        current_component = self.held_components.get(self.current_component_name)
        if current_component is None:
            return self.place_holder
        return self.held_components.get(self.current_component_name).widget()

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
