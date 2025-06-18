import logging
from typing import Callable, Dict, Optional

LOGGER = logging.getLogger(__name__)


class ComponentRegistry:

    def __init__(self):
        super().__init__()
        self.registry: Dict[str, dict] = {}

    def register_component(self, name: str, component_data: dict) -> None:
        """
        Register a component with the structure expected by App.

        Args:
            name: Component name
            component_data: Complete structure with definition and instances

        Raises:
            ValueError: If name is empty or if structure is invalid
        """
        if not name or not isinstance(name, str):
            raise ValueError("Component name must be a non-empty string")

        if not isinstance(component_data, dict):
            raise ValueError("Component data must be a dictionary")

        # Validate data structure
        self._validate_component_data(component_data)

        if name in self.registry:
            LOGGER.warning(f"Component '{name}' already registered, replacing...")

        self.registry[name] = component_data
        LOGGER.debug(f"Component '{name}' registered successfully")

    def _validate_component_data(self, component_data: dict) -> None:
        """
        Validate the structure of component data.

        Args:
            component_data: Data to validate

        Raises:
            ValueError: If structure is invalid
        """
        required_keys = {"definition", "instances"}
        if not all(key in component_data for key in required_keys):
            raise ValueError(f"Structure must contain keys: {required_keys}")

        definition = component_data["definition"]
        if not isinstance(definition, dict):
            raise ValueError("'definition' must be a dictionary")

        required_def_keys = {"class", "instantiation_policy", "instantiate_on"}
        if not all(key in definition for key in required_def_keys):
            raise ValueError(f"'definition' must contain keys: {required_def_keys}")

    def get_component_def(self, name: str) -> Optional[dict]:
        """
        Get the definition of a component.

        Args:
            name: Component name

        Returns:
            Optional[dict]: Component definition or None if not found
        """
        component_data = self.registry.get(name)
        return component_data["definition"] if component_data else None

    def get_component_data(self, name: str) -> Optional[dict]:
        """
        Get complete data for a component (definition + instances).

        Args:
            name: Component name

        Returns:
            Optional[dict]: Complete component data or None if not found
        """
        return self.registry.get(name)

    def get_all_components(self) -> Dict[str, dict]:
        """
        Return a read-only view of all registered components.

        Note: Returns a copy to avoid external modifications.

        Returns:
            Dict[str, dict]: View of the component registry
        """
        return dict(self.registry)

    def is_component_registered(self, name: str) -> bool:
        """
        Check if a component is registered.

        Args:
            name: Name of the component to check

        Returns:
            bool: True if the component is registered
        """
        return name in self.registry

    def get_component_count(self) -> int:
        """
        Return the number of registered components.

        Returns:
            int: Number of components in the registry
        """
        return len(self.registry)

    def get_components_by_policy(self, policy: str) -> Dict[str, dict]:
        """
        Return all components with a given instantiation policy.

        Args:
            policy: Instantiation policy ("singleton" or "multi")

        Returns:
            Dict[str, dict]: Components matching the policy
        """
        return {
            name: component_data
            for name, component_data in self.registry.items()
            if component_data["definition"]["instantiation_policy"] == policy
        }

    def clear_registry(self) -> None:
        """
        Completely clear the component registry.
        Recommended use only for testing.
        """
        LOGGER.warning("Complete clearing of component registry")
        self.registry.clear()


# Decorator to register components
def register_app_component(
    name: str, policy: str = "singleton", instantiation_time: str = "setup"
) -> Callable:
    """
    Register a component in the global registry.

    Args:
        name: Unique component name
        policy: "singleton" | "multi" - Instantiation policy
        instantiation_time: "setup" | "demand" - Instantiation time
    Returns:
        Callable:
    """
    # Parameter validation
    if policy not in ["singleton", "multi"]:
        raise ValueError(
            f"Policy '{policy}' invalid. Accepted values: singleton, multi"
        )

    if instantiation_time not in ["setup", "demand"]:
        raise ValueError(
            f"Instantiation time '{instantiation_time}' invalid. Accepted values: setup, demand"
        )

    def decorator(cls: type) -> type:
        # Corrected structure to match App expectations
        APP_COMPONENT_REGISTRY.register_component(
            name,
            {
                "definition": {
                    "class": cls,
                    "instantiation_policy": policy,
                    "instantiate_on": instantiation_time,
                },
                "instances": {},
            },
        )
        return cls

    return decorator


# Global registry instance
APP_COMPONENT_REGISTRY = ComponentRegistry()
