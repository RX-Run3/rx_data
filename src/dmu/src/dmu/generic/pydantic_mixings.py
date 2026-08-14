'''
Module holding useful mixings for pydantic models
'''
import pandas as pnd

from pathlib   import Path
from typing    import Protocol, Sequence, TypeVar, Any
from functools import cached_property

T_co = TypeVar('T_co', covariant = True)
# ---------------------------
class _RootModelProtocol(Protocol[T_co]):
    '''
    Protocol meant to represent frozen RootModel
    '''
    @property
    def root(self) -> T_co: ...
# ---------------------------
class _SupportsModelDumpJson(Protocol):
    def model_dump_json(self, *, indent: int) -> str: ...
# ---------------------------
class Serializable:
    '''
    Implements:

    to_json
    '''
    # ---------------------------
    def to_json(self : _SupportsModelDumpJson, path : Path) -> None:
        '''
        Parameters
        ---------------
        path: Path to JSON file where current object will be serialized
        '''
        path.parent.mkdir(parents = True, exist_ok = True)

        string = self.model_dump_json(indent = 2)
        path.write_text(string)
# ---------------------------
class _GridElement(Protocol[T_co]):
    '''
    Protocol meant to symbolize grid elements
    '''
    @property
    def wp(self) -> T_co: ...
# ---------------------------
class GridProtocol(_RootModelProtocol[Sequence[_GridElement]], Protocol):
    '''
    Protocol for containers consistent with grids
    '''
    @cached_property
    def df(self) -> pnd.DataFrame: ...

    def model_copy(
        self,
        *,
        update: dict[str, Any] | None = None,
        deep  : bool = False) -> "GridProtocol": ...
# ---------------------------
class Patchable:
    '''
    Implements:

    patch
    '''
    # ----------------------------------------------
    @staticmethod
    def __find_missing(points : Sequence[_GridElement]) -> Sequence[_GridElement]:
        '''
        Parameters
        ----------------
        points: Collection of grid elements

        Returns
        ----------------
        Collection of missing grid elements in input
        '''
        return [] 
    # ----------------------------------------------
    def patch(self : GridProtocol) -> GridProtocol:
        '''
        Patches missing elements in grid
        '''
        missing = Patchable.__find_missing(points = self.root)
        all_pts = [ *missing , *self.root ]

        return self.model_copy(update = {'root' : all_pts}) 
# ---------------------------
