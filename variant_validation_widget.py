import PySide6.QtWidgets as qw


class VariantValidationWidget(qw.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._layout = qw.QVBoxLayout()

        self.setLayout(self._layout)

    def on_variant_selected(self, variant_dict):
        pass
