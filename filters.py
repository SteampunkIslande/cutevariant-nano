from enum import Enum
from typing import List


class FilterType(Enum):
    AND = "AND"
    OR = "OR"
    LEAF = "LEAF"


class FilterExpression:
    def __init__(
        self,
        filter_type=FilterType.LEAF,
        expression: str = None,
        parent: "FilterExpression" = None,
    ) -> None:
        if filter_type is FilterType.LEAF and not expression:
            raise ValueError("Leaf filter must have an expression")
        if filter_type is not FilterType.LEAF and expression:
            raise ValueError("Non-leaf filter must not have an expression")
        self.filter_type = filter_type
        self.expression = expression
        self.children: List["FilterExpression"] = []
        self.parent = parent
        if self.parent:
            self.parent.add_child(self)

    def add_child(self, child: "FilterExpression"):
        self.children.append(child)
        child.parent = self
        return child

    def __bool__(self) -> bool:
        if self.filter_type == FilterType.LEAF:
            return bool(self.expression)
        else:
            return bool(self.children)

    def __str__(self) -> str:
        if self.filter_type == FilterType.LEAF:
            return self.expression
        else:
            if self.parent:
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
    def from_json(json) -> "FilterExpression":
        if "filter_type" in json:
            filter_type = FilterType(json["filter_type"])
            new_filter = FilterExpression(filter_type)
            for child in json["children"]:
                new_filter.add_child(FilterExpression.from_json(child))
            return new_filter
        elif "expression" in json:
            return FilterExpression(FilterType.LEAF, json["expression"])
        else:
            raise ValueError(
                "Cannot deserialize filter expression from this JSON, malformed!"
            )


if __name__ == "__main__":
    root = FilterExpression(FilterType.AND)
    aeq_5 = root.add_child(FilterExpression(FilterType.LEAF, "a = 5"))
    beq_6 = root.add_child(FilterExpression(FilterType.LEAF, "b = 6"))
    first_or = root.add_child(FilterExpression(FilterType.OR))
    first_or.add_child(FilterExpression(FilterType.LEAF, "c = 7"))
    first_or.add_child(FilterExpression(FilterType.LEAF, "d = 8"))
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
    new_root = FilterExpression.from_json(serialized)
    assert str(new_root) == str(root)
    assert str(root) == "a = 5 AND b = 6 AND (c = 7 OR d = 8)"
