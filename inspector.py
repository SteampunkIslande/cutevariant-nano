import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

from datalake import DataLake
from fields_widget import FieldsWidget
from filters_widget import FiltersWidget
from order_by_widget import OrderByWidget
from query_table_widget import QueryTableWidget
from validation_widget import ValidationWidgetContainer
from variant_validation_widget import VariantValidationWidget


class Inspector(qw.QWidget):

    def __init__(
        self, datalake: DataLake, query_table_widget: QueryTableWidget, parent=None
    ):
        super().__init__(parent)

        self._layout = qw.QVBoxLayout()

        self._splitter = qw.QSplitter(qc.Qt.Orientation.Vertical)

        self.datalake = datalake

        self.query_table_widget = query_table_widget

        self.main_widget = qw.QTabWidget()

        # Add another widget below the tab widget, to display variants information in another tab widget
        self.variant_widget = qw.QTabWidget()

        self._splitter.addWidget(self.main_widget)
        self._splitter.addWidget(self.variant_widget)

        self._layout.addWidget(self._splitter)

        self.main_tabs = {}
        self.variant_tabs = {}

        self.setLayout(self._layout)

        self.setup()

    def setup(self):
        self.validation_widget_container = ValidationWidgetContainer(
            self.datalake,
            self.query_table_widget,
        )
        self.filters_widget = FiltersWidget(self.datalake.get_query("validation"))
        self.order_by_widget = OrderByWidget(self.datalake.get_query("validation"))
        self.fields_widget = FieldsWidget(self.datalake.get_query("validation"))

        self.main_widget.addTab(
            self.validation_widget_container, qc.QCoreApplication.tr("Source")
        )
        self.main_widget.addTab(
            self.filters_widget, qc.QCoreApplication.tr("Filtres de validation")
        )
        self.main_widget.addTab(
            self.order_by_widget, qc.QCoreApplication.tr("Tri des colonnes")
        )
        self.main_widget.addTab(
            self.fields_widget, qc.QCoreApplication.tr("Nom des colonnes")
        )
        self.main_tabs["validation"] = self.validation_widget_container
        self.main_tabs["filters"] = self.filters_widget
        self.main_tabs["fields"] = self.fields_widget

        self.variant_validation_widget = VariantValidationWidget(
            self.datalake.get_query("validation"),
            self.query_table_widget,
            self.validation_widget_container.validation_widget,
        )
        self.variant_widget.addTab(
            self.variant_validation_widget,
            qc.QCoreApplication.tr("Validation des variants"),
        )
        self.variant_tabs["variant_validation"] = self.variant_validation_widget

        # self.variant_info_widget = VariantInfoWidget(
        #     self.validation_widget_container.validation_widget, self.query_table_widget
        # )
        # self.variant_widget.addTab(
        #     self.variant_info_widget,
        #     qc.QCoreApplication.tr("Informations sur les variants"),
        # )
        # self.variant_tabs["variant"] = self.variant_info_widget
