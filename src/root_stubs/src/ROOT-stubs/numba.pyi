from collections.abc import Callable, Sequence
from typing import ParamSpec, TypeVar

_P = ParamSpec("_P")
_R = TypeVar("_R")


class Numba:
    @staticmethod
    def Declare(
        arg_types: Sequence[str],
        return_type: str | None = None,
        name: str | None = None,
    ) -> Callable[
        [Callable[_P, _R]],
        Callable[_P, _R],
    ]: ...
