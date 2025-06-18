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

    def remove_component_instance(
        self, component_name: str, instance_name: str
    ) -> bool:
        """
        Remove a specific instance from a component.

        Args:
            component_name: Name of the component
            instance_name: Name of the instance to remove

        Returns:
            bool: True if successfully removed, False otherwise
        """
        if component_name not in self.registry:
            LOGGER.warning(f"Component '{component_name}' not found in registry")
            return False

        component_data = self.registry[component_name]
        instances = component_data["instances"]

        if instance_name not in instances:
            LOGGER.debug(
                f"Instance '{instance_name}' not found in component '{component_name}'"
            )
            return True  # Already removed, consider success

        del instances[instance_name]
        LOGGER.debug(
            f"Removed instance '{instance_name}' from component '{component_name}'"
        )
        return True

    def get_active_instances(self) -> Dict[str, list]:
        """
        Get all active instances grouped by component.

        Returns:
            Dict[str, list]: Dictionary mapping component names to lists of instance names
        """
        return {
            component_name: list(component_data["instances"].keys())
            for component_name, component_data in self.registry.items()
            if component_data["instances"]
        }

    def get_total_instance_count(self) -> int:
        """
        Get the total number of active component instances.

        Returns:
            int: Total number of instances across all components
        """
        return sum(
            len(component_data["instances"])
            for component_data in self.registry.values()
        )

    def validate_registry_integrity(self) -> list:
        """
        Validate the integrity of the component registry.

        Returns:
            list: List of issues found (empty if no issues)
        """
        issues = []

        for component_name, component_data in self.registry.items():
            if not isinstance(component_data, dict):
                issues.append(f"Component '{component_name}' data is not a dictionary")
                continue

            if "definition" not in component_data:
                issues.append(f"Component '{component_name}' missing definition")

            if "instances" not in component_data:
                issues.append(f"Component '{component_name}' missing instances")
                continue

            instances = component_data["instances"]
            if not isinstance(instances, dict):
                issues.append(
                    f"Component '{component_name}' instances is not a dictionary"
                )
                continue

            for instance_name, instance in instances.items():
                if instance is None:
                    issues.append(
                        f"Component '{component_name}' has None instance '{instance_name}'"
                    )
                elif not hasattr(instance, "component_name"):
                    issues.append(
                        f"Instance '{instance_name}' of '{component_name}' missing component_name attribute"
                    )
                elif instance.component_name != component_name:
                    issues.append(
                        f"Instance '{instance_name}' component_name mismatch: expected '{component_name}', got '{instance.component_name}'"
                    )

        return issues


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
