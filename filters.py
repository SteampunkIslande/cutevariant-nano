from enum import Enum
from typing import List


class FilterType(Enum):
    AND = "AND"
    OR = "OR"
    LEAF = "LEAF"
    ROOT = "ROOT"


class FilterItem:

    def __init__(
        self,
        filter_type=FilterType.LEAF,
        expression: str = None,
        alias: str = None,
        parent: "FilterItem" = None,
    ) -> None:
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
        self.alias = alias

    def internal_move(self, new_parent: "FilterItem", new_row: int):
        if (
            self.filter_type == FilterType.LEAF
            and new_parent.filter_type == FilterType.LEAF
        ):
            raise ValueError("Cannot move leaf filter into another leaf filter")
        if self._parent:
            self._parent.children.remove(self)
            new_parent.children.insert(new_row, self)
            self._parent = new_parent

    def add_child(self, child: "FilterItem"):
        if self.filter_type != FilterType.LEAF:
            if child not in self.children:
                self.children.append(child)
                child._parent = self
            else:
                print("Child already exists", child)
            return child
        else:
            self._parent.add_child(child)

    def child(self, row: int) -> "FilterItem":
        if self.filter_type != FilterType.LEAF and row < len(self.children):
            return self.children[row]

    def parent(self) -> "FilterItem":
        return self._parent

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
            if self._parent and self._parent.filter_type != FilterType.ROOT:
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
        # (Invisible) root item
        if not self.parent():
            return {
                "filter_type": self.filter_type.value,
                "children": [child.to_json() for child in self.children],
            }
        if self.filter_type == FilterType.LEAF:
            return {
                "filter_type": self.filter_type.value,
                "expression": self.expression,
                "alias": self.alias,
            }
        else:
            return {
                "filter_type": self.filter_type.value,
                "children": [child.to_json() for child in self.children],
                "alias": self.alias,
            }

    @classmethod
    def from_json(cls, data: dict, parent: "FilterItem" = None):
        root = FilterItem(
            FilterType(data["filter_type"]),
            data.get("expression"),
            data.get("alias"),
            parent,
        )
        if "children" in data:
            for child_data in data["children"]:
                root.add_child(cls.from_json(child_data, root))
        return root


if __name__ == "__main__":
    root = FilterItem(FilterType.ROOT)
    first_node = root.add_child(FilterItem(FilterType.AND))
    aeq_5 = first_node.add_child(FilterItem(FilterType.LEAF, "a = 5"))
    beq_6 = first_node.add_child(FilterItem(FilterType.LEAF, "b = 6"))
    first_or = first_node.add_child(FilterItem(FilterType.OR))
    first_or.add_child(FilterItem(FilterType.LEAF, "c = 7"))
    first_or.add_child(FilterItem(FilterType.LEAF, "d = 8"))
    serialized = root.to_json()
    assert serialized == {
        "filter_type": "ROOT",
        "children": [
            {
                "filter_type": "AND",
                "children": [
                    {"filter_type": "LEAF", "expression": "a = 5", "alias": None},
                    {"filter_type": "LEAF", "expression": "b = 6", "alias": None},
                    {
                        "filter_type": "OR",
                        "children": [
                            {
                                "filter_type": "LEAF",
                                "expression": "c = 7",
                                "alias": None,
                            },
                            {
                                "filter_type": "LEAF",
                                "expression": "d = 8",
                                "alias": None,
                            },
                        ],
                        "alias": None,
                    },
                ],
                "alias": None,
            }
        ],
    }
    new_root = FilterItem.from_json(serialized)

    assert str(new_root) == str(root)
    print(str(new_root))
    # assert str(root) == "a = 5 AND b = 6 AND (c = 7 OR d = 8)"
