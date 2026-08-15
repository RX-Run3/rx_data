'''
Module with protocol classes for pydantic classes
'''
import pandas as pnd

from typing    import Protocol, Sequence, TypeVar, Any, Self
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
class SupportsModelDumpJson(Protocol):
    def model_dump_json(self, *, indent: int) -> str: ...
# ---------------------------
class NodeLocProtocol(_RootModelProtocol[Sequence], Protocol):
    '''
    Protocol representing the location of a node in a grid
    '''
# ---------------------------
Loc_co = TypeVar('Loc_co', bound = NodeLocProtocol, covariant = True)
class GridElementProtocol(Protocol[Loc_co]):
    '''
    Protocol meant to symbolize grid elements
    '''
    @property
    def val(self) -> float: ...

    @property
    def err(self) -> float: ...

    @property
    def wp(self) -> Loc_co: ...
# ---------------------------
T_loc_contra = TypeVar('T_loc_contra', bound = NodeLocProtocol    , contravariant =  True)
T_elem       = TypeVar('T_elem'      , bound = GridElementProtocol, covariant     = False)
class GridProtocol(_RootModelProtocol[Sequence[T_elem]], Protocol[T_loc_contra, T_elem]):
    '''
    Protocol for containers consistent with grids
    '''
    @cached_property
    def df(self) -> pnd.DataFrame: ...

    def at(self, wp : T_loc_contra, fall_back : T_elem | None) -> T_elem: ...

    def model_copy(
        self,
        *,
        update: dict[str, Any] | None = None,
        deep  : bool = False) -> Self: ...
# ---------------------------
