import json
from pathlib import Path
import PySide6.QtWidgets as qw

import app as ap
import query_manager.query_manager_component as qmc
from component_registry import register_app_component

DEFAULT_QUERY = {
    "select": {
        "fields": [
            "'#'||\"Background color\" AS 'Etiquette'",
            "'#'||\"VAF color\" as '.vafcolor'",
            '"Sample_id"',
            '"PREDICTED"',
            '"Project.recurrence"',
            '"Project.recurrence.DENOM"',
            '"Analysis_recurrence.N"',
            '"Analysis.recurrence.DENOM"',
            '"Glims"',
            '"Exon.rank"',
            '"Gene.symbol"',
            '"Chrom"',
            '"Position"',
            '"N.Ref"',
            '"N.Alt"',
            '"VAF"',
            '"Variant.effect"',
            '"hgvs.p"',
            '"Depth"',
            '"NbrReadRef"',
            '"NbrReadAlt"',
            '"NbrReadAlt.Pos"',
            '"NbrReadAlt.Neg"',
            '"Feature.id"',
            '"hgvs.c"',
            '"dbsnp.rs.id"',
            '"Cosmic.noncoding.id"',
            '"Cosmic.coding.id"',
            '"Recurrence.cosmic"',
            '"Nombre_reference.cosmic"',
            '"Histo_majoritaire.cosmic"',
            '"Histo_majoritaire_pourcentage.cosmic"',
            '"Clinvar.clinical.significance"',
            '"Clinvar.review.status"',
            '"MAF"',
            '"Position_recurrenceB"',
            '"Position_recurrence1B"',
            '"Position_recurrence1_detail.N"',
            '"is.driver"',
            '"Temps"',
            '"ORIGINE"',
            '"RatioAlt_PosNeg"',
            '"testN.R"',
            '"testN.D"',
            '"testN_recurrence"',
            '"testN_id.N"',
            '"Feature.type"',
            '"SIFT"',
            '"PROVEAN"',
            '"Phastcons"',
            '"Spidex.dpsi.max.tissue"',
            '"dbscsnv.Ada.score"',
            '"dbscsnv.Rf.score"',
            '"Putative.impact"',
            '"CADD.phred"',
            '"FATHMM"',
            '"MUTATIONTASTER"',
            '"Read.background.enrichment"',
            '"Torrent.server.metric"',
            '"Fisher.test.p.value"',
            '"Spidex.dpsi.z.score"',
            '"NbrReadRef.Pos"',
            '"NbrReadRef.Neg"',
            '"NChar_Alt"',
            '"NChar_Ref"',
            '"SDlong"',
            '"dlong"',
            '"rlong"',
            '"Depth_min"',
            '"SDlong.1"',
            '"dlong.1"',
            '"rlong.1"',
            '"Gene.mediane"',
            '"Position.mediane1"',
            '"Position.mediane"',
            '"Position.medianeR"',
            '"VAFsum"',
            '"NChar_Alt.median"',
            '"NChar_Ref.median"',
            '"RatioAlt_PosNeg.Sample_id"',
            '"RatioAlt_PosNeg.median1"',
            '"Test"',
            '"TRI"',
        ],
        "tables": [{"expression": "{main_table}", "alias": "main_table"}],
        "filter": {
            "filter_type": "AND",
            "children": [
                {"expression": "main_table.\"VAF color\" = 'FFFF0000'"},
                {
                    "expression": "main_table.\"Background color\" NOT IN ('FF000000', '000000')"
                },
            ],
        },
        "order_by": [
            {"field": "main_table.Chrom", "order": "ASC"},
            {"field": "main_table.Position", "order": "ASC"},
        ],
    }
}


@register_app_component(
    name="generic_explorer", policy="singleton", instantiation_time="demand"
)
class GenericExplorerComponent(ap.AppComponent):

    component_name = "generic_explorer"

    def __init__(self, app: ap.App, instance_name: str, parent: qw.QWidget = None):
        super().__init__(app, instance_name)

        self._widget = qw.QWidget(parent)
        self._layout = qw.QVBoxLayout(self._widget)
        self._widget.setLayout(self._layout)

        self._widget.setWindowTitle(self.app.translate("Generic Explorer"))

        self.app = app

        # Get the query manager component and its widget
        self.query_manager: qmc.QueryManagerComponent = self.app.get_component(
            "query_manager"
        )
        self.query_manager_widget = self.query_manager.widget()

        self.add_query_btn = qw.QPushButton(self.app.translate("Add Query"))

        # Add widgets to the main layout
        self._layout.addWidget(self.query_manager_widget)
        self._layout.addWidget(self.add_query_btn)

        self.generic_queries: dict[str, dict] = {}

        # Connect button to handler
        self.add_query_btn.clicked.connect(self.on_add_query)

    def load_from_session(self, session):
        self.generic_queries = session.get("generic_queries", {})
        for query_name, query_info in self.generic_queries.items():
            with open(query_info["path"], "r") as f:
                query_definition = json.load(f)
                print(query_definition)
            self.query_manager.new_generic_query(
                ui_name=query_name,
                query_definition=query_definition,
                readonly_files=query_info.get("readonly_files", ["*.parquet"]),
            )

    def save_to_session(self):
        return {
            "generic_queries": self.generic_queries,
        }

    def widget(self):
        return self._widget

    def on_add_query(self):
        # Ask for a query name
        # Then ask for file names

        query_name, ok = qw.QInputDialog.getText(
            self._widget,
            self.app.translate("New Query"),
            self.app.translate("Enter query name:"),
        )
        if not ok or not query_name:
            return
        # Ask for file names
        file_names, ok = qw.QInputDialog.getText(
            self._widget,
            self.app.translate("New Query"),
            self.app.translate("Enter file names (comma separated):"),
        )
        if not ok or not file_names:
            return

        file_names = [name.strip() for name in file_names.split(",") if name.strip()]

        if not file_names:
            qw.QMessageBox.warning(
                self._widget,
                self.app.translate("Invalid Input"),
                self.app.translate("No valid file names provided."),
            )
            return

        # Create a new query
        query = self.query_manager.new_generic_query(
            ui_name=query_name,
            query_definition=DEFAULT_QUERY,
            readonly_files=file_names,
        )

        serialized_path = (
            (
                Path(query.datalake.datalake_path)
                / "queries"
                / "Requêtes génériques"
                / (query_name + ".json")
            )
            if query
            else None
        )
        # Add this new path to the list of generic queries paths
        if serialized_path:
            self.generic_queries[query_name] = {
                "path": str(serialized_path),
                "readonly_files": file_names,
            }
