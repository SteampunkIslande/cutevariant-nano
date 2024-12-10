import PySide6.QtWebEngineWidgets as qwe
import PySide6.QtWidgets as qw

from query_table_widget import QueryTableWidget
from validation_widget import ValidationWidget

# Add a new widget to display variant information


class VariantInfoWidget(qw.QWidget):

    def __init__(
        self,
        validation_widget: ValidationWidget,
        query_table_widget: QueryTableWidget,
        parent=None,
    ):
        super().__init__(parent)

        self.validation_widget = validation_widget
        self.query_table_widget = query_table_widget

        self._layout = qw.QVBoxLayout()

        self.combobox = qw.QComboBox()
        # Read URL templates from settings

        self.validation_widget.method_changed.connect(self.update_combobox)

        self._layout.addWidget(self.combobox)

        # A webview with a combobox to select variant info website

        self.webview = qwe.QWebEngineView()
        self._layout.addWidget(self.webview)

        self.query_table_widget.selection_changed.connect(
            self.on_current_variant_changed
        )

        self.setLayout(self._layout)

    def update_combobox(self):
        self.combobox.clear()
        if self.validation_widget.method is not None:
            url_templates = self.validation_widget.method.get(
                "variant_info_url_templates"
            )
            if url_templates is not None:
                for url_template in url_templates:
                    self.combobox.addItem(url_template["name"], url_template["url"])

    def on_current_variant_changed(self):
        variant_id = self.query_table_widget.get_current_validation_hashes()
        self.update_current_variant(variant_id)

    def update_current_variant(self, variant_id: dict):
        # url: str = self.combobox.currentData()
        # variant_id = {re.sub(r"^\.", "", k): v for k, v in variant_id.items()}
        # url = url.format(**{k: v for k, v in variant_id.items() if v})
        # self.webview.setUrl(qc.QUrl(url))
        pass
