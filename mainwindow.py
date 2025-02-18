import PySide6.QtCore as qc
import PySide6.QtWidgets as qw


class MainWindow(qw.QMainWindow):

    def __init__(self, parent=None, flags=qc.Qt.WindowType.Desktop):
        super().__init__(parent, flags)

        # Create the main vertical splitter
        self.vertical_splitter = qw.QSplitter()
        self.vertical_splitter.setOrientation(qc.Qt.Orientation.Vertical)

        # Create the left tab widget
        self.left_tab_widget = qw.QTabWidget()
        self.vertical_splitter.addWidget(self.left_tab_widget)

        # Create the right horizontal splitter
        self.horizontal_splitter = qw.QSplitter()
        self.horizontal_splitter.setOrientation(qc.Qt.Orientation.Horizontal)

        # Create the tab widgets for the horizontal splitter
        self.lower_widget = qw.QTabWidget()
        self.horizontal_splitter.addWidget(self.lower_widget)

        # Add the horizontal splitter to the vertical splitter
        self.vertical_splitter.addWidget(self.horizontal_splitter)

        # Set the central widget of the main window
        self.setCentralWidget(self.vertical_splitter)

        self.upper_widget = None

    def set_upper_widget(self, widget: qw.QWidget):
        self.upper_widget = widget
        self.horizontal_splitter.insertWidget(0, self.upper_widget)


if __name__ == "__main__":
    import sys

    app = qw.QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()
