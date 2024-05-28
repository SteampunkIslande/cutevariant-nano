#!/usr/bin/env python

from typing import List

import PySide6.QtWidgets as qw

from common_widgets.searchable_list import SearchableList


class StringListChooser(qw.QDialog):

    def __init__(self, items: List[str], parent=None):
        super().__init__(parent)

        self.items = items
        self.widget = SearchableList(items)

        self.ok_cancel = qw.QDialogButtonBox()
        self.ok_cancel.setStandardButtons(
            qw.QDialogButtonBox.StandardButton.Ok
            | qw.QDialogButtonBox.StandardButton.Cancel
        )

        layout = qw.QVBoxLayout()
        layout.addWidget(self.widget)
        layout.addWidget(self.ok_cancel)

        self.setLayout(layout)

        self.ok_cancel.accepted.connect(self.accept)
        self.ok_cancel.rejected.connect(self.reject)

    def get_selected(self) -> List[str]:
        return self.widget.get_selected()
