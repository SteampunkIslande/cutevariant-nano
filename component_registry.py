# component_registry.py
from typing import Callable, Dict

APP_COMPONENT_REGISTRY: Dict[str, dict] = {}


def register_app_component(
    name: str, policy: str = "singleton", instantiation_time: str = "setup"
) -> Callable:
    """Décorateur pour enregistrer les composants dans le registre global."""

    def decorator(cls: type) -> type:
        APP_COMPONENT_REGISTRY[name] = {
            "class": cls,
            "instantiation_policy": policy,
            "instantiate_on": instantiation_time,
        }
        return cls

    return decorator
