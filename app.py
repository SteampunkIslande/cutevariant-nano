from abc import ABC, abstractmethod
from typing import List

import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal


class App:
    def __init__(self):
        self.main_window = qw.QMainWindow()
        self.components = {}

    def register_components(self):
        # To be able to compile with nuitka, manually import all the components in the project.
        # If you'd like your own component to be included, just add it to the source folder and import it here
        import datalake_component

        datalake_component.register_component()

    def register_component(self, component_name: str, component_definition: dict):
        self.components[component_name] = {
            "definition": component_definition,
            "instances": {},
        }

    def window(self):
        return self.main_window

    def setup_app(self):
        for component_name, component in self.components.items():
            if component["definition"]["instantiate_on"] == "setup":
                self.instantiate_component(
                    component_name=component_name,
                    instantiation_policy=component["definition"][
                        "instantiation_policy"
                    ],
                    actions=component["definition"]["actions"],
                )

    def start(self):
        for component_name in self.components:
            for _, instance in self.components[component_name]["instances"].items():
                instance.on_start()

    def instantiate_component(
        self, component_name: str, instantiation_policy: str, actions: List[str]
    ):
        if self.components[component_name]["instantiation_policy"] == "singleton":
            if len(self.components[component_name]["instances"]) == 1:
                return
            else:
                self.components[component_name]["instances"][0] = self.components[
                    component_name
                ]["class"](self, 0)

        highest_instance_id = max(self.components[component_name]["instances"].keys())
        self.components[component_name]["instances"]

        for action in actions:
            pass

    def get_component_instance(self, component_name: str, instance_id: int):
        component_info = self.components.get(component_name)


class AppComponent(ABC):

    # Signal is emitted whenever the internal state of this component changed.
    state_changed = Signal(dict)

    @abstractmethod
    def __init__(self, app: App, instance_id: int):
        pass

    @abstractmethod
    def on_start(self):
        """Here is the place to connect to required components. They should exist"""
        pass

    @abstractmethod
    def on_action_triggered(self):
        pass

    @abstractmethod
    def get_signal(self, signal_name: str):
        pass


if __name__ == "__main__":
    app = App()
