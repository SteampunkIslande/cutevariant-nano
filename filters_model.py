import PySide6.QtCore as qc

from filters import FilterItem, FilterType


class FiltersItemModel(qc.QAbstractItemModel):

    def __init__(self, root_item: FilterItem, parent: qc.QObject = None):
        super().__init__(parent)
        self.root = root_item

        self.root.child_added.connect(self.on_child_added)

    def index(self, row: int, column: int, parent: qc.QModelIndex = qc.QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return qc.QModelIndex()
        parent_item = parent.internalPointer() if parent.isValid() else self.root
        child_item = parent_item.children[row]
        if child_item:
            return self.createIndex(row, column, child_item)
        else:
            return qc.QModelIndex()

    def parent(self, index: qc.QModelIndex):
        if not index.isValid():
            return qc.QModelIndex()
        child_item: FilterItem = index.internalPointer()
        parent_item = child_item._parent
        if parent_item == self.root:
            return qc.QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent: qc.QModelIndex):
        if parent.column() > 0:
            return 0
        parent_item = parent.internalPointer() if parent.isValid() else self.root
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

    def on_child_added(self, parent: FilterItem, row: int):
        self.beginInsertRows(self.createIndex(parent.row(), 0, parent), row, row)
        self.endInsertRows()

    def flags(self, index: qc.QModelIndex):
        if not index.isValid():
            return qc.Qt.ItemFlag.NoItemFlags
        return qc.Qt.ItemFlag.ItemIsEnabled | qc.Qt.ItemFlag.ItemIsSelectable
