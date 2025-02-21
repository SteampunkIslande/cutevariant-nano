import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

from query.query import Query

# Class for a custom editor for the order by widget (for the first column, add a combobox with the field names, and for the second column, add a combobox with the order options (ASC, DESC))


class OrderByWidgetItemDelegate(qw.QStyledItemDelegate):

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)
        self.query = query

    def createEditor(self, parent, option, index):
        if index.column() == 0:
            editor = qw.QComboBox(parent)
            editor.addItems(self.query.list_exposed_fields())
        if index.column() == 1:
            editor = qw.QComboBox(parent)
            editor.addItems(["ASC", "DESC"])

        return editor

    def setEditorData(self, editor: qw.QComboBox, index):
        if index.column() == 0:
            editor.setCurrentText(index.model().data(index))
        if index.column() == 1:
            editor.setCurrentText(index.model().data(index))

    def setModelData(self, editor: qw.QComboBox, model, index):
        if index.column() == 0:
            model.setData(index, {"field": editor.currentText()})
        if index.column() == 1:
            model.setData(index, {"order": editor.currentText()})

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class OrderByWidget(qw.QWidget):
    def __init__(self, query: Query, parent=None):
        super().__init__(parent)

        self.query = query

        self._layout = qw.QVBoxLayout()
        self.setLayout(self._layout)

        self.setup_model_view()

        self._layout.addStretch()

        self.show()

    def setup_model_view(self):
        self.order_by_view = qw.QTableView(self)
        self.order_by_model = self.query.order_by_model

        self.order_by_delegate = OrderByWidgetItemDelegate(self.query, self)

        self.order_by_view.setModel(self.order_by_model)
        self.order_by_view.setItemDelegate(self.order_by_delegate)
        self.order_by_view.setSelectionBehavior(
            qw.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.order_by_view.setSelectionMode(
            qw.QAbstractItemView.SelectionMode.SingleSelection
        )

        self.order_by_view.horizontalHeader().setSectionResizeMode(
            qw.QHeaderView.ResizeMode.ResizeToContents
        )
        self.order_by_view.horizontalHeader().setSectionResizeMode(
            0, qw.QHeaderView.ResizeMode.Stretch
        )
        self.order_by_view.horizontalHeader().setSectionResizeMode(
            1, qw.QHeaderView.ResizeMode.Stretch
        )

        self.order_by_view.setDragDropMode(
            qw.QAbstractItemView.DragDropMode.InternalMove
        )
        self.order_by_view.setDragEnabled(True)

        self.order_by_view.setContextMenuPolicy(
            qc.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.order_by_view.customContextMenuRequested.connect(
            self.context_menu_requested
        )

        self._layout.addWidget(self.order_by_view)

    def context_menu_requested(self, p: qc.QPoint):
        menu = qw.QMenu()

        remove_action: qg.QAction = menu.addAction(
            qc.QCoreApplication.tr("Remove order by")
        )
        remove_action.triggered.connect(self.remove_order_by)

        menu.exec(qg.QCursor.pos())

    def remove_order_by(self):
        selected_indexes = self.order_by_view.selectedIndexes()
        if selected_indexes:
            self.order_by_model.removeRow(selected_indexes[0].row())
