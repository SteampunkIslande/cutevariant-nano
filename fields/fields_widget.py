import PySide6.QtWidgets as qw

import app as ap
import fields.fields_model as fldm
from common_widgets.searchable_list import SearchableList


class FieldsWidget(qw.QWidget):
    def __init__(self, app: ap.App, model: fldm.FieldsModel):
        super().__init__()

        self.app = app
        self.model = model

        self.searchable_list = SearchableList(self.model)
        self.searchable_list.view.setDragDropMode(
            qw.QAbstractItemView.DragDropMode.InternalMove
        )

        layout = qw.QVBoxLayout(self)
        layout.addWidget(self.searchable_list)
        self.setLayout(layout)
