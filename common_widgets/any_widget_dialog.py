import PySide6.QtWidgets as qw


class AnyWidgetDialog(qw.QDialog):
    def __init__(self, widget: qw.QWidget, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._layout = qw.QVBoxLayout()
        self._layout.addWidget(widget)

        self.dialog_buttons = qw.QDialogButtonBox(
            qw.QDialogButtonBox.StandardButton.Ok
            | qw.QDialogButtonBox.StandardButton.Cancel
        )
        self.dialog_buttons.accepted.connect(self.accept)
        self.dialog_buttons.rejected.connect(self.reject)

        self._layout.addStretch()
        self._layout.addWidget(self.dialog_buttons)

        self.setLayout(self._layout)

        self.show()
