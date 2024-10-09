import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

from filters import FilterItem, FilterType
from query import Query


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
        pass

    def setup_filters_label(self):
        """Adds a label that displays current filters in the query, as the SQL (nested) string. This label
        is updated whenever the filters are changed.
        """
        self._filters_label = qw.QLabel(self)
        self.model.model_changed.connect(self.update_filters_label)

        self._layout.addWidget(self._filters_label)

    def update_filters_label(self):
        self._filters_label.setText(
            "<b>Resulting filter:</b><br/>" + str(self.query.filter_model)
        )

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
        print(item.filter_type, item.expression)

        add_filter_action = menu.addAction("Add expression filter")
        add_filter_action.triggered.connect(lambda: self.add_filter(FilterType.LEAF))

        add_filter_and_action = menu.addAction("Add AND filter")
        add_filter_and_action.triggered.connect(lambda: self.add_filter(FilterType.AND))

        add_filter_or_action = menu.addAction("Add OR filter")
        add_filter_or_action.triggered.connect(lambda: self.add_filter(FilterType.OR))

        remove_filter_action = menu.addAction("Remove filter")
        remove_filter_action.triggered.connect(self.remove_filter)

        menu.exec_(self.filters_view.viewport().mapToGlobal(pos))
