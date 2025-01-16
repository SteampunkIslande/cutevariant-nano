import json
from html import escape

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

from commons import get_last_session_path
from filters import FilterItem, FilterType
from filters_model import FilterModel
from query import Query


# A simple table view with each row being a filter shown to the user as a string.
# The default string is the SQL representation of the filter. The user can edit the filter by double-clicking on it.
# Everytime the filters model is changed, we add a row to the table view.
class FiltersHistoryWidget(qw.QWidget):

    def __init__(self, filters_model: FilterModel, parent=None):
        super().__init__(parent)

        self._layout = qw.QVBoxLayout()

        self.filters_model = filters_model
        self.filters_model.model_changed.connect(self.update_table)

        self.model = qg.QStandardItemModel(0, 2, self)

        self.table = qw.QTableView(self)

        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().hide()
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(
            qw.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(qw.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setModel(self.model)

        self._layout.addWidget(self.table)

        self.load_model_from_session()

        self.setLayout(self._layout)

        qw.QApplication.instance().aboutToQuit.connect(self.save_filter_history)

        # Add context menu to remove filters from the history, and to apply them to the current query

        self.setup_actions()
        self.table.setContextMenuPolicy(qc.Qt.ContextMenuPolicy.ActionsContextMenu)

    def load_model_from_session(self):
        last_session_path = get_last_session_path()
        if last_session_path:
            with open(last_session_path, "r") as f:
                last_session = json.load(f)
                if "filter_history" in last_session:
                    for hist_item in last_session["filter_history"]:
                        # hist_item is a dict with keys "alias" and a json representation of the filter item
                        filter_item = FilterItem.from_json(hist_item["filter_item"])
                        alias = hist_item["alias"]
                        alias_item = qg.QStandardItem(alias)
                        alias_item.setEditable(True)

                        filter_item_item = qg.QStandardItem(str(filter_item))
                        filter_item_item.setData(
                            filter_item, qc.Qt.ItemDataRole.UserRole
                        )
                        filter_item_item.setEditable(False)

                        self.model.appendRow(
                            [
                                alias_item,
                                filter_item_item,
                            ]
                        )

    def update_table(self):
        # Add the last filter to the table, if it is not already there
        last_filter_item = self.filters_model._rootItem
        last_filter_str = str(last_filter_item)

        for row in range(self.model.rowCount()):
            filter_repr = self.model.item(row, 1).text()
            if filter_repr == last_filter_str:
                return

        last_filter_item_item = qg.QStandardItem(last_filter_str)
        last_filter_item_item.setData(last_filter_item, qc.Qt.ItemDataRole.UserRole)
        last_filter_item_item.setEditable(False)

        alias_item = qg.QStandardItem("Alias")
        alias_item.setEditable(True)

        self.model.appendRow(
            [
                alias_item,
                last_filter_item_item,
            ]
        )

        self.save_filter_history()

    def save_filter_history(self):
        last_session_path = get_last_session_path()
        if last_session_path:
            with open(last_session_path, "r") as f:
                last_session = json.load(f)
                last_session["filter_history"] = []

                for row in range(self.model.rowCount()):
                    alias = self.model.item(row, 0).text()
                    filter_item: FilterItem = self.model.item(row, 1).data(
                        qc.Qt.ItemDataRole.UserRole
                    )
                    last_session["filter_history"].append(
                        {
                            "alias": alias,
                            "filter_item": filter_item.to_json(),
                        }
                    )

            with open(last_session_path, "w") as f:
                json.dump(last_session, f)

    def setup_actions(self):
        self.remove_filter_action = qg.QAction("Remove filter", self)
        self.remove_filter_action.setShortcut(qg.QKeySequence(qc.Qt.Key.Key_Delete))
        self.remove_filter_action.triggered.connect(self.remove_filter)

        self.apply_filter_action = qg.QAction("Apply filter to query", self)
        self.apply_filter_action.setShortcut(qg.QKeySequence(qc.Qt.Key.Key_Return))
        self.apply_filter_action.triggered.connect(self.apply_filter)

        self.table.addActions([self.remove_filter_action, self.apply_filter_action])

    def remove_filter(self):
        index = self.table.currentIndex()
        if not index.isValid():
            return
        self.model.removeRow(index.row())

    def apply_filter(self):
        index = self.table.currentIndex()
        if not index.isValid():
            return
        filter_item: FilterItem = index.siblingAtColumn(1).data(
            qc.Qt.ItemDataRole.UserRole
        )
        self.filters_model.load(filter_item.to_json())


class FiltersWidgetItemDelegate(qw.QStyledItemDelegate):

    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        # TODO: Would be best to use index.data() to determine the type of editor to create
        item: FilterItem = index.internalPointer()
        if item.filter_type == FilterType.LEAF:
            editor = qw.QLineEdit(parent)
            return editor
        if item.filter_type in (FilterType.AND, FilterType.OR):
            editor = qw.QComboBox(parent)
            editor.addItem("AND")
            editor.addItem("OR")
            return editor

    def setEditorData(self, editor: qw.QLineEdit | qw.QComboBox, index):
        item: FilterItem = index.internalPointer()
        if item.filter_type == FilterType.LEAF:
            editor.setText(item.expression)
        if item.filter_type in (FilterType.AND, FilterType.OR):
            editor.setCurrentText(item.filter_type.value)

    def setModelData(self, editor: qw.QLineEdit | qw.QComboBox, model, index):
        item: FilterItem = index.internalPointer()
        if item.filter_type == FilterType.LEAF:
            model.setData(index, {"expression": editor.text()})
        elif item.filter_type in (FilterType.AND, FilterType.OR):
            model.setData(index, {"filter_type": editor.currentText()})

    def updateEditorGeometry(self, editor, option: qw.QStyleOptionViewItem, index):
        editor.setGeometry(option.rect)


class FiltersWidget(qw.QWidget):
    def __init__(self, query: Query, parent=None):
        super().__init__(parent)
        self.query = query

        self._layout = qw.QVBoxLayout()
        self.setLayout(self._layout)

        self.setup_model_view()
        self.setup_query_variables()
        self.setup_filters_label()
        self.setup_filter_history()

        self._layout.addStretch()

        self.show()

    def setup_model_view(self):
        self.filters_view = qw.QTreeView(self)

        self.filters_view_item_delegate = FiltersWidgetItemDelegate(self)
        self.filters_view.setItemDelegate(self.filters_view_item_delegate)

        # Add context menu with actions to add, remove, and move filters
        self.filters_view.setContextMenuPolicy(
            qc.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.filters_view.customContextMenuRequested.connect(
            self.context_menu_requested
        )
        self.filters_view.setDragDropMode(
            qw.QAbstractItemView.DragDropMode.InternalMove
        )
        self.filters_view.setDragEnabled(True)
        self.model = self.query.filter_model
        self.filters_view.setModel(self.model)

        self._layout.addWidget(self.filters_view)

    def setup_query_variables(self):
        # self.query_variables_widget =
        pass

    def setup_filter_history(self):
        self.filter_history = FiltersHistoryWidget(self.model, self)

        self._layout.addWidget(self.filter_history)

    def setup_filters_label(self):
        """Adds a label that displays current filters in the query, as the SQL (nested) string. This label
        is updated whenever the filters are changed.
        """
        self._filters_label = qw.QLabel(self)
        self._filters_label.setTextInteractionFlags(
            qc.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.model.model_changed.connect(self.update_filters_label)

        self._layout.addWidget(self._filters_label)

    def update_filters_label(self):
        self._filters_label.setText(
            "<b>Resulting filter:</b><br/>" + escape(str(self.model))
        )
        self._filters_label.setWordWrap(True)

    def add_filter(self, filter_type: FilterType):
        index = self.filters_view.currentIndex()

        parent_item: FilterItem = index.internalPointer()
        while parent_item.filter_type == FilterType.LEAF:
            index = index.parent()
            parent_item = index.internalPointer()

        if not index.isValid():
            return
        if filter_type == FilterType.LEAF:
            expression, ok = qw.QInputDialog.getText(
                self, "Expression", "Enter expression"
            )
            if ok:
                item = FilterItem(FilterType.LEAF, expression, alias=None, parent=None)
                self.model.add_child(index, item)
        else:
            item = FilterItem(filter_type, None, alias=None, parent=None)
            self.model.add_child(index, item)

    def remove_filter(self):
        index = self.filters_view.currentIndex()
        if not index.isValid():
            return
        self.model.remove_child(index)

    def context_menu_requested(self, pos):
        menu = qw.QMenu(self)

        index = self.filters_view.indexAt(pos)
        item: FilterItem = index.internalPointer()

        add_filter_action = menu.addAction("Add expression filter")
        add_filter_action.triggered.connect(lambda: self.add_filter(FilterType.LEAF))

        add_filter_and_action = menu.addAction("Add AND filter")
        add_filter_and_action.triggered.connect(lambda: self.add_filter(FilterType.AND))

        add_filter_or_action = menu.addAction("Add OR filter")
        add_filter_or_action.triggered.connect(lambda: self.add_filter(FilterType.OR))

        remove_filter_action = menu.addAction("Remove filter")
        remove_filter_action.triggered.connect(self.remove_filter)

        menu.exec_(self.filters_view.viewport().mapToGlobal(pos))
