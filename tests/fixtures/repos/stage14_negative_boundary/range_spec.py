from __future__ import annotations


class RangeSpec:
    def __init__(self, lower: int, upper: int, include_lower: bool, include_upper: bool) -> None:
        self.lower = lower
        self.upper = upper
        self.include_lower = include_lower
        self.include_upper = include_upper

    @classmethod
    def parse(cls, text: str) -> "RangeSpec":
        include_lower = text[0] == "["
        include_upper = text[-1] == "]"
        lower_text, upper_text = text[1:-1].split(",", 1)
        return cls(int(lower_text), int(upper_text), include_lower, include_upper)

    def contains(self, value: int) -> bool:
        return self.lower <= value <= self.upper
