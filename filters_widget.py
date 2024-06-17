import PySide6.QtWidgets as qw

import filters as flt
import filters_model as fltm


class FiltersWidget(qw.QWidget):
    def __init__(self, filter_root: flt.FilterItem, parent=None):
        super().__init__(parent)

        self._layout = qw.QVBoxLayout()
        self.setLayout(self._layout)

        self.filters = qw.QTreeView(self)
        self.model = fltm.FiltersItemModel(filter_root, self)
        self.filters.setModel(self.model)

        self._layout.addWidget(self.filters)

        self._layout.addStretch()

        self.show()
