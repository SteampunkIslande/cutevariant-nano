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

        self._widgets = {
            "Run name": self.run_name_label,
            "Sample name": self.sample_name_label,
            "Chromosome": self.chromosome_label,
            "Position": self.position_label,
            "Ref": self.ref_label,
            "Alt": self.alt_label,
            "Accepted": self.accepted_cb,
            "Comment": self.comment_te,
            "Tags": self.tags_te,
        }

        self.setLayout(self._layout)

    def on_current_variant_changed(self):
        validation_hashes = self.query_table_widget.get_current_validation_hashes()
        if validation_hashes:
            validation_hash = validation_hashes[0]
            self.update_view(validation_hash)

    def update_view(self, validation_hash: int):
        method = self.validation_widget.method
        info_fields: dict[str, str] = method.get("info_fields", {})

        query_cols = list(info_fields.values())
        info = self.query.get_variant_info(validation_hash, query_cols)

        self.run_name_label.setText(str(info.get(info_fields["Run name"], "")))
        self.sample_name_label.setText(str(info.get(info_fields["Sample name"], "")))
        self.chromosome_label.setText(str(info.get(info_fields["Chromosome"], "")))
        self.position_label.setText(str(info.get(info_fields["Position"], "")))
        self.ref_label.setText(str(info.get(info_fields["Ref"], "")))
        self.alt_label.setText(str(info.get(info_fields["Alt"], "")))
        self.accepted_cb.setChecked(info.get(info_fields["Accepted"], False) or False)
        self.comment_te.setPlainText(info.get(info_fields["Comment"], ""))
        self.tags_te.setPlainText(info.get(info_fields["Tags"], ""))
