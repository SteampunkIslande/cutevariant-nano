import logging
import weakref
from enum import Enum
from functools import partial

import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

import app as ap

LOGGER = logging.getLogger(__name__)


class WindowRegion(Enum):

    LEFT = 0
    UPPER = 1
    LOWER = 2
    RIGHT = 3


class MainWindow(qw.QMainWindow):

    closing = qc.Signal()

    def __init__(self, app: "ap.App"):
        super().__init__()

        self.horizontal_splitter = qw.QSplitter()
        self.horizontal_splitter.setOrientation(qc.Qt.Orientation.Horizontal)

        self.left_tab_widget = qw.QTabWidget()

        self.vertical_splitter = qw.QSplitter()
        self.vertical_splitter.setOrientation(qc.Qt.Orientation.Vertical)

        self.lower_tab_widget = qw.QTabWidget()
        self.upper_tab_widget = qw.QTabWidget()
        self.vertical_splitter.addWidget(self.upper_tab_widget)
        self.vertical_splitter.addWidget(self.lower_tab_widget)

        self.right_tab_widget = qw.QTabWidget()

        self.horizontal_splitter.addWidget(self.left_tab_widget)
        self.horizontal_splitter.addWidget(self.vertical_splitter)
        self.horizontal_splitter.addWidget(self.right_tab_widget)

        self.widget_regions = {
            WindowRegion.LEFT: self.left_tab_widget,
            WindowRegion.UPPER: self.upper_tab_widget,
            WindowRegion.LOWER: self.lower_tab_widget,
            WindowRegion.RIGHT: self.right_tab_widget,
        }
        for _, widget in self.widget_regions.items():
            widget.setMovable(True)

        self.setCentralWidget(self.horizontal_splitter)
        screen_size = qw.QApplication.screens()[0].geometry()
        width = screen_size.width()
        height = screen_size.height()
        left = screen_size.left()
        top = screen_size.top()

        self.setGeometry(
            int(left + (width) / 4),
            int(top + (height) / 4),
            int((width) / 2),
            int(top + (height) / 2),
        )

        left_tab_size = self.width() // 5
        right_tab_size = self.width() // 5
        central_tab_size = self.width() - left_tab_size - right_tab_size

        self.horizontal_splitter.setSizes(
            [left_tab_size, central_tab_size, right_tab_size]
        )

        self.closing_components_handlers = {}
        self.title_update_handlers = {}

        self.app = app

    def add_component_to_window(
        self, component: "ap.AppComponent", region: WindowRegion
    ):
        if component.widget() is None:
            return

        tab_widget = self.widget_regions[region]
        tab_widget.addTab(component.widget(), component.widget().windowTitle())

        self.closing_components_handlers[component.instance_name] = partial(
            self.on_component_closing, weakref.proxy(component), region
        )

        self.title_update_handlers[component.instance_name] = partial(
            self.update_component_title, weakref.proxy(component), region=region
        )

        component.closing.connect(
            self.closing_components_handlers[component.instance_name]
        )
        component.widget().windowTitleChanged.connect(
            self.title_update_handlers[component.instance_name]
        )

    def on_component_closing(self, component: "ap.AppComponent", region: WindowRegion):
        LOGGER.debug(
            f"Closing component {component.instance_name} in region {region.name}"
        )
        tab_widget = self.widget_regions[region]
        tab_index = tab_widget.indexOf(component.widget())
        if tab_index != -1:
            tab_widget.removeTab(tab_index)
            component.closing.disconnect(
                self.closing_components_handlers[component.instance_name]
            )
            component.widget().windowTitleChanged.disconnect(
                self.title_update_handlers[component.instance_name]
            )
            del self.closing_components_handlers[component.instance_name]
        else:
            LOGGER.warning(
                f"Component {component.instance_name} not found in region {region.name} tab widget."
            )

    def update_component_title(
        self, component: "ap.AppComponent", new_title: str, region: WindowRegion
    ):
        tab_widget = self.widget_regions[region]
        tab_index = tab_widget.indexOf(component.widget())
        if tab_index != -1:
            tab_widget.setTabText(tab_index, new_title)
            component.widget().setWindowTitle(new_title)

    def get_window_panel(self, region: WindowRegion):
        return self.widget_regions[region]

    def closeEvent(self, event):
        confirmation = qw.QMessageBox.question(
            self,
            self.app.translate("Closing"),
            self.app.translate(
                "Are you sure you want to close? Everything will be saved automatically."
            ),
            qw.QMessageBox.StandardButton.Yes,
            qw.QMessageBox.StandardButton.No,
        )
        if confirmation == qw.QMessageBox.StandardButton.Yes:
            # Emits the signal, waiting for every receiver to respond to it
            self.closing.emit()
            event.accept()
        else:
            event.ignore()


if __name__ == "__main__":
    import sys

    app = qw.QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()
