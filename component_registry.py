from typing import Callable, Dict

from PySide6.QtCore import QObject, Signal


class ComponentRegistry(QObject):
    componentDestroyed = Signal(str)  # Signal émis avec le nom de l'instance détruite

    def __init__(self):
        super().__init__()
        self.registry: Dict[str, dict] = {}

    def register_component(self, name: str, component_def: dict):
        self.registry[name] = component_def

    def get_component_def(self, name: str) -> dict:
        return self.registry.get(name)


# Décorateur pour enregistrer les composants
def register_app_component(
    name: str, policy: str = "singleton", instantiation_time: str = "setup"
) -> Callable:
    def decorator(cls: type) -> type:
        # Enregistrer le composant dans le registre global
        APP_COMPONENT_REGISTRY.register_component(
            name,
            {
                "class": cls,
                "instantiation_policy": policy,
                "instantiate_on": instantiation_time,
            },
        )
        return cls

    return decorator


# Instance globale du registre
APP_COMPONENT_REGISTRY = ComponentRegistry()
