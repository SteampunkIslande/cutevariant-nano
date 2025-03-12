import PySide6.QtCore as qc
from PySide6.QtCore import SignalInstance
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

import app


class WidgetHolderComponent(app.AppComponent):
    """Allows one widget to hold several AppComponents at the same time, only displaying one at a time. This component is not responsible for choosing, but rather the component that's using it."""

    current_component_changed = qc.Signal(str)

    def __init__(
        self,
        app: app.App,
        instance_name: str,
        parent_component: app.AppComponent = None,
    ):
        super().__init__(app, instance_name, parent_component)

        self.held_components: dict[str, "app.AppComponent"] = {}
        self.current_component_name = None

        self._layout = QVBoxLayout()
        self._layout_widget = QWidget()
        self._layout_widget.setLayout(self._layout)

        self.place_holder = QLabel(f"Instance::{instance_name}. No component shown.")
        self.place_holder.setWindowTitle(instance_name)

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

        return self.set_current_component(component_name)

    def remove_component(self, component_name: str):
        if component_name not in self.held_components:
            return False
        if self.current_component_name == component_name:
            self.current_component_name = None
        del self.held_components[component_name]

        return self.update_widget()

    def set_current_component(self, component_name: str):
        if component_name not in self.held_components:
            self.current_component_name = None
        if self.current_component_name == component_name:
            return False
        self.current_component_name = component_name
        return self.update_widget()

    def set_title(self, title: str):
        self._layout_widget.setWindowTitle(title)

    def widget(self):
        return self._layout_widget

    def update_widget(self) -> QWidget:

        # Empty the layout
        while self._layout.count():
            item = self._layout.takeAt(0)
            item.widget().hide()
            self._layout.removeItem(item)

        # Current component name is not set: show placeholder
        if self.current_component_name is None:
            self._layout_widget.setWindowTitle(self.place_holder.windowTitle())
            self._layout.addWidget(self.place_holder)
            return False

        current_component = self.held_components.get(self.current_component_name)
        # Component is not found: show placeholder
        if current_component is None:
            self._layout_widget.setWindowTitle(self.place_holder.windowTitle())
            self._layout.addWidget(self.place_holder)
            return False

        current_widget = current_component.widget()
        # Component has no widget: show placeholder
        if current_widget is None:
            self._layout_widget.setWindowTitle(self.place_holder.windowTitle())
            self._layout.addWidget(self.place_holder)
            return False

        self._layout.addWidget(current_widget)
        self._layout_widget.setWindowTitle(current_component.get_instance_name())

        current_widget.show()

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
