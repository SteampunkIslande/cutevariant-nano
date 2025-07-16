import logging

import PySide6.QtCore as qc
import PySide6.QtWidgets as qw


LOGGER = logging.getLogger(__name__)


class QueryManagerWidget(qw.QWidget):

    current_query_changed = qc.Signal(str)

    query_renamed = qc.Signal(str, str)

    def __init__(self, model: qc.QAbstractItemModel, parent: qw.QWidget = None):
        super().__init__(parent)

        self._layout = qw.QVBoxLayout(self)
        self.query_list_view = qw.QListView(self)
        self.model = model

        self._layout.addWidget(self.query_list_view)

        self.query_list_view.setModel(model)
        self.query_list_view.selectionModel().selectionChanged.connect(
            self.on_current_query_changed
        )

        self.setLayout(self._layout)

    def set_current_query(self, query_instancename: str):
        if self.model:
            self.query_list_view.selectionModel().select(
                self.model.match(
                    self.model.index(0, 0),
                    qc.Qt.ItemDataRole.UserRole,
                    query_instancename,
                    1,
                    qc.Qt.MatchFlag.MatchExactly,
                )[0],
                qc.QItemSelectionModel.SelectionFlag.ClearAndSelect,
            )

    def on_current_query_changed(self):
        indexes = self.query_list_view.selectionModel().selectedIndexes()
        if not indexes:
            return
        current = indexes[0]
        if not current.isValid():
            return
        # Either None or empty string
        if not current.data(qc.Qt.ItemDataRole.UserRole):
            return
        self.current_query_changed.emit(current.data(qc.Qt.ItemDataRole.UserRole))
