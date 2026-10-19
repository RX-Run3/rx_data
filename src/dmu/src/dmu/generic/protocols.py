from typing import Protocol, Self

class SupportsAddition(Protocol):
    def __add__(self, other: Self, /) -> Self: ...
