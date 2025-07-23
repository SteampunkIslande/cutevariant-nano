import logging
from typing import Union

import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import app as ap
import query.query_component as q
from component_registry import register_app_component

LOGGER = logging.getLogger(__name__)

# NOT IMPORTED YET
# Just keeping the code here before I decide whether or not to use it.


@register_app_component(
    name="query_analyzer", policy="singleton", instantiation_time="setup"
)
class QueryAnalyzerComponent(ap.AppComponent):
    """
    Query Analyzer Component

    This component provides analysis functionality for queries.
    It tracks the currently selected query and provides a menu entry
    to trigger analysis methods.
    """

    component_name = "query_analyzer"

    def __init__(self, app: ap.App, instance_name: str):
        super().__init__(app, instance_name)
        LOGGER.debug(
            f"Instantiating QueryAnalyzerComponent with instance name: {instance_name}"
        )

        # Track the currently selected query
        self.current_query: Union[q.QueryComponent, None] = None

        # Create the menu action for query analysis
        self.analyze_query_action = qg.QAction(self.app.translate("Analyze Query"))
        self.analyze_query_action.triggered.connect(self.analyze_current_query)

        self.app.selected_query_changed.connect(self.on_selected_query_changed)

        # Initially disable the action since no query is selected
        self.analyze_query_action.setEnabled(False)

    def on_selected_query_changed(self):
        """Handle when the selected query changes."""
        # Get the currently selected query from the app
        new_query = self.app.get_current_query()

        if new_query != self.current_query:
            self.current_query = new_query

            # Update action availability based on whether we have a query
            self.analyze_query_action.setEnabled(self.current_query is not None)

    def get_menubar_entries(self) -> list[tuple[str, qg.QAction]]:
        """Return menu bar entries for this component."""
        return [
            (self.app.translate("Analysis"), self.analyze_query_action),
        ]

    def analyze_current_query(self):
        pass

    def widget(self) -> Union[None, qw.QWidget]:
        """This component doesn't provide a widget."""
        return None

    def save_to_session(self) -> dict:
        """Save component state to session."""
        # Nothing to save for this simple component
        return {}

    def load_from_session(self, session: dict):
        """Load component state from session."""
        # Nothing to load for this simple component
        pass

    def close_component(self):
        """Clean up when the component is closed."""
        self.app.selected_query_changed.disconnect(self.on_selected_query_changed)
        self.current_query = None
        self.analyze_query_action = None
        super().close_component()
