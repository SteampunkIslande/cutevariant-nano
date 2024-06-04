import PySide6.QtWidgets as qw


class MultiLineDisplay(qw.QWidget):

    def __init__(self, parent: qw.QWidget = None):
        super().__init__(parent)
        self._layout = qw.QVBoxLayout()
        self.setLayout(self._layout)

        self.text_edit = qw.QTextEdit()
        self.text_edit.setReadOnly(True)
        self._layout.addWidget(self.text_edit)
