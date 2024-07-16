import PySide6.QtCore as qc

from filters import FilterItem, FilterType


class FiltersItemModel(qc.QAbstractItemModel):

    def __init__(self, root_item: FilterItem, parent: qc.QObject = None):
        super().__init__(parent)
        self.invisible_root = FilterItem(FilterType.AND)
        self.root = root_item
        self.invisible_root.add_child(self.root)

    def index(self, row: int, column: int, parent: qc.QModelIndex = qc.QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return qc.QModelIndex()
        if not parent.isValid():
            parent_item = self.invisible_root
        else:
            parent_item = parent.internalPointer()
        child_item = parent_item.children[row]
        if child_item:
            return self.createIndex(row, column, child_item)
        return qc.QModelIndex()

    def parent(self, index: qc.QModelIndex):
        if not index.isValid():
            return qc.QModelIndex()
        child_item: FilterItem = index.internalPointer()
        parent_item = child_item._parent
        if parent_item == self.invisible_root or parent_item is None:
            return qc.QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent: qc.QModelIndex):
        if parent.column() > 0:
            return 0
        if not parent.isValid():
            parent_item = self.invisible_root
        else:
            parent_item = parent.internalPointer()
        return parent_item.child_count()

    def columnCount(self, parent: qc.QModelIndex):
        return 1

    def data(self, index: qc.QModelIndex, role: int):
        if not index.isValid():
            return None
        if role == qc.Qt.ItemDataRole.DisplayRole:
            item: FilterItem = index.internalPointer()
            if item.filter_type == FilterType.LEAF:
                return item.expression
            else:
                return item.filter_type.value
        return None

    def headerData(self, section: int, orientation: qc.Qt.Orientation, role: int):
        if (
            orientation == qc.Qt.Orientation.Horizontal
            and role == qc.Qt.ItemDataRole.DisplayRole
            and section == 0
        ):
            return "Filters"
        return None

    def flags(self, index: qc.QModelIndex):
        if not index.isValid():
            return qc.Qt.ItemFlag.NoItemFlags
        return qc.Qt.ItemFlag.ItemIsEnabled | qc.Qt.ItemFlag.ItemIsSelectable

    def add_filter(
        self, parent: qc.QModelIndex, filter_type: FilterType, expression: str
    ):
        self.beginInsertRows(parent, 0, 0)
        parent_item = parent.internalPointer() if parent.isValid() else self.root
        new_filter = FilterItem(filter_type, expression)
        parent_item.add_child(new_filter)
        self.endInsertRows()
