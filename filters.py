from enum import Enum
from typing import List

import PySide6.QtCore as qc


class FilterType(Enum):
    AND = "AND"
    OR = "OR"
    LEAF = "LEAF"


class FilterItem(qc.QObject):

    child_added = qc.Signal(object, int)

    def __init__(
        self,
        filter_type=FilterType.LEAF,
        expression: str = None,
        parent: "FilterItem" = None,
    ) -> None:
        super().__init__(parent)
        if filter_type is FilterType.LEAF and not expression:
            raise ValueError("Leaf filter must have an expression")
        if filter_type is not FilterType.LEAF and expression:
            raise ValueError("Non-leaf filter must not have an expression")
        self.filter_type = filter_type
        self.expression = expression
        self.children: List["FilterItem"] = []
        self._parent = parent
        if self._parent:
            self._parent.add_child(self)

    def internal_move(self, new_parent: "FilterItem", new_row: int):
        self._parent.children.remove(self)
        new_parent.children.insert(new_row, self)
        self._parent = new_parent

    def add_child(self, child: "FilterItem"):
        self.children.append(child)
        child._parent = self
        self.child_added.emit(self, child.row())
        return child

    def child_count(self) -> int:
        return len(self.children)

    def column_count(self) -> int:
        return 1

    def __bool__(self) -> bool:
        if self.filter_type == FilterType.LEAF:
            return bool(self.expression)
        else:
            return bool(self.children)

    def row(self) -> int:
        if self._parent:
            return self._parent.children.index(self)
        return 0

    def __str__(self) -> str:
        if self.filter_type == FilterType.LEAF:
            return self.expression
        else:
            if self._parent:
                return (
                    "("
                    + f" {self.filter_type.value} ".join(
                        [f"{child}" for child in self.children]
                    )
                    + ")"
                )
            else:
                return f" {self.filter_type.value} ".join(
                    [f"{child}" for child in self.children]
                )

    def to_json(self):
        if self.filter_type == FilterType.LEAF:
            return {"expression": self.expression}
        else:
            return {
                "filter_type": self.filter_type.value,
                "children": [child.to_json() for child in self.children],
            }

    @staticmethod
    def from_json(json) -> "FilterItem":
        if "filter_type" in json:
            filter_type = FilterType(json["filter_type"])
            new_filter = FilterItem(filter_type)
            for child in json["children"]:
                new_filter.add_child(FilterItem.from_json(child))
            return new_filter
        elif "expression" in json:
            return FilterItem(FilterType.LEAF, json["expression"])
        else:
            raise ValueError(
                "Cannot deserialize filter expression from this JSON, malformed!"
            )


if __name__ == "__main__":
    root = FilterItem(FilterType.AND)
    aeq_5 = root.add_child(FilterItem(FilterType.LEAF, "a = 5"))
    beq_6 = root.add_child(FilterItem(FilterType.LEAF, "b = 6"))
    first_or = root.add_child(FilterItem(FilterType.OR))
    first_or.add_child(FilterItem(FilterType.LEAF, "c = 7"))
    first_or.add_child(FilterItem(FilterType.LEAF, "d = 8"))
    serialized = root.to_json()
    assert serialized == {
        "filter_type": "AND",
        "children": [
            {"expression": "a = 5"},
            {"expression": "b = 6"},
            {
                "filter_type": "OR",
                "children": [{"expression": "c = 7"}, {"expression": "d = 8"}],
            },
        ],
    }
    new_root = FilterItem.from_json(serialized)
    assert str(new_root) == str(root)
    assert str(root) == "a = 5 AND b = 6 AND (c = 7 OR d = 8)"
