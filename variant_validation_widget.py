import PySide6.QtWidgets as qw

import query as q
from query_table_widget import QueryTableWidget
from validation_widget import ValidationWidget


class VariantValidationWidget(qw.QWidget):

    def __init__(
        self,
        query: "q.Query",
        query_table_widget: QueryTableWidget,
        validation_widget: ValidationWidget,
        parent=None,
    ):
        super().__init__(parent)

        self.query = query
        self.query_table_widget = query_table_widget
        self.validation_widget = validation_widget

        self.query_table_widget.selection_changed.connect(
            self.on_current_variant_changed
        )

        self._layout = qw.QFormLayout()

        # Create form layout with run_name,sample_name,chromosome,position,ref,alt,accepted(checkbox),comment(textbox, editable), and tags(textbox, editable)

        self.run_name_label = qw.QLabel()
        self.sample_name_label = qw.QLabel()
        self.chromosome_label = qw.QLabel()
        self.position_label = qw.QLabel()
        self.ref_label = qw.QLabel()
        self.alt_label = qw.QLabel()
        self.accepted_cb = qw.QCheckBox()
        self.comment_te = qw.QTextEdit()
        self.tags_te = qw.QTextEdit()

        self._layout.addRow("Run Name", self.run_name_label)
        self._layout.addRow("Sample Name", self.sample_name_label)
        self._layout.addRow("Chromosome", self.chromosome_label)
        self._layout.addRow("Position", self.position_label)
        self._layout.addRow("Ref", self.ref_label)
        self._layout.addRow("Alt", self.alt_label)
        self._layout.addRow("Accepted", self.accepted_cb)
        self._layout.addRow("Comment", self.comment_te)
        self._layout.addRow("Tags", self.tags_te)

        self.setLayout(self._layout)

    def on_current_variant_changed(self):
        variant_id = self.query_table_widget.get_current_variant_ids()[0]
        self.update_view(variant_id)

    def update_view(self, variant_id: int):
        pass
