#!/usr/bin/env python3
"""
Test script for component lifecycle management improvements.
This script validates that components are properly cleaned up and removed from the registry.
"""

import logging
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

import PySide6.QtWidgets as qw

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

LOGGER = logging.getLogger(__name__)


def test_component_lifecycle():
    """Test the enhanced component lifecycle management."""

    LOGGER.info("Starting component lifecycle test...")

    # Create Qt application
    app_qt = qw.QApplication(sys.argv)

    try:
        # Import after Qt is initialized
        from app import App
        from component_registry import APP_COMPONENT_REGISTRY

        # Create app instance
        app = App(app_options={"debug": True})

        LOGGER.info("App created successfully")

        # Check initial component state
        initial_components = APP_COMPONENT_REGISTRY.get_active_instances()
        initial_count = APP_COMPONENT_REGISTRY.get_total_instance_count()

        LOGGER.info(f"Initial component count: {initial_count}")
        LOGGER.info(f"Initial components: {initial_components}")

        # Validate registry integrity
        integrity_issues = APP_COMPONENT_REGISTRY.validate_registry_integrity()
        if integrity_issues:
            LOGGER.warning(f"Registry integrity issues found: {integrity_issues}")
        else:
            LOGGER.info("Registry integrity check passed")

        # Test instantiating a validation manager component
        LOGGER.info("Testing component instantiation...")
        validation_manager = app.instantiate_component("validation_manager")

        if validation_manager:
            LOGGER.info(
                f"Validation manager instantiated: {validation_manager.get_instance_name()}"
            )

            # Check component count after instantiation
            after_instantiation_count = (
                APP_COMPONENT_REGISTRY.get_total_instance_count()
            )
            LOGGER.info(
                f"Component count after instantiation: {after_instantiation_count}"
            )

            # Test explicit component cleanup
            LOGGER.info("Testing explicit component cleanup...")
            validation_manager.close_component()

            # Check component count after cleanup
            after_cleanup_count = APP_COMPONENT_REGISTRY.get_total_instance_count()
            LOGGER.info(f"Component count after cleanup: {after_cleanup_count}")

            if after_cleanup_count < after_instantiation_count:
                LOGGER.info("✓ Component successfully removed from registry")
            else:
                LOGGER.warning("⚠ Component may not have been properly removed")

        # Test application shutdown cleanup
        LOGGER.info("Testing application shutdown cleanup...")

        # Show final component state
        final_components = APP_COMPONENT_REGISTRY.get_active_instances()
        final_count = APP_COMPONENT_REGISTRY.get_total_instance_count()

        LOGGER.info(f"Final component count before shutdown: {final_count}")
        LOGGER.info(f"Final components: {final_components}")

        # Trigger app close (this should call _force_cleanup_all_components)
        app.on_close()

        # Check component count after shutdown
        shutdown_count = APP_COMPONENT_REGISTRY.get_total_instance_count()
        shutdown_components = APP_COMPONENT_REGISTRY.get_active_instances()

        LOGGER.info(f"Component count after shutdown: {shutdown_count}")
        LOGGER.info(f"Components after shutdown: {shutdown_components}")

        if shutdown_count == 0:
            LOGGER.info("✓ All components successfully cleaned up during shutdown")
        else:
            LOGGER.warning(f"⚠ {shutdown_count} components still remain after shutdown")

        LOGGER.info("Component lifecycle test completed")

    except Exception as e:
        LOGGER.error(f"Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Clean up Qt application
        app_qt.quit()

    return True


if __name__ == "__main__":
    success = test_component_lifecycle()
    sys.exit(0 if success else 1)
