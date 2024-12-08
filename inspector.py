import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

from datalake import DataLake
from filters_widget import FiltersWidget
from order_by_widget import OrderByWidget
from validation_widget import ValidationWidgetContainer

from variant_info_widget import VariantInfoWidget
from query_table_widget import QueryTableWidget


class Inspector(qw.QWidget):

    def __init__(
        self, datalake: DataLake, query_table_widget: QueryTableWidget, parent=None
    ):
        super().__init__(parent)

        self._layout = qw.QVBoxLayout()

        self.datalake = datalake

        self.query_table_widget = query_table_widget

        self.main_widget = qw.QTabWidget()

        # Add another widget below the tab widget, to display variants information in another tab widget
        self.variant_widget = qw.QTabWidget()

        self._layout.addWidget(self.main_widget)
        self._layout.addWidget(self.variant_widget)

        self.main_tabs = {}
        self.variant_tabs = {}

        self.setLayout(self._layout)

        self.setup()

    def setup(self):
        self.validation_widget = ValidationWidgetContainer(
            self.datalake, self.query_table_widget
        )
        self.filters_widget = FiltersWidget(self.datalake.get_query("validation"))
        self.order_by_widget = OrderByWidget(self.datalake.get_query("validation"))

        self.main_widget.addTab(
            self.validation_widget, qc.QCoreApplication.tr("Validation")
        )
        self.main_widget.addTab(
            self.filters_widget, qc.QCoreApplication.tr("Filtres de validation")
        )
        self.main_widget.addTab(
            self.order_by_widget, qc.QCoreApplication.tr("Tri des colonnes")
        )
        self.main_tabs["validation"] = self.validation_widget
        self.main_tabs["filters"] = self.filters_widget

        self.variant_info_widget = VariantInfoWidget(
            self.validation_widget.validation_widget, self.query_table_widget
        )
        self.variant_widget.addTab(
            self.variant_info_widget,
            qc.QCoreApplication.tr("Informations sur les variants"),
        )
        self.variant_tabs["variant"] = self.variant_info_widget
