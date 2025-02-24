from enum import Enum

import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

import app as ap


class WindowRegion(Enum):

    LEFT = 0
    UPPER = 1
    LOWER = 2
    RIGHT = 3


class MainWindow(qw.QMainWindow):

    def __init__(self):
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

    def add_component_to_window(self, component: ap.AppComponent, region: WindowRegion):
        if component.widget() is None:
            return

        print(component.widget(), component.get_instance_name())
        # TODO: If needed, maybe we should store this into component
        tab_index = self.widget_regions[region].addTab(
            component.widget(), component.widget().windowTitle()
        )


if __name__ == "__main__":
    import sys

    app = qw.QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()
