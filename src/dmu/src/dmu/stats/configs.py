'''
Module with classes meant to represent configurations needed to build yields
'''

from typing   import Literal, Self, Final
from pydantic import BaseModel, model_validator
from pydantic import RootModel

_MIN_COMPOSITE_PARS : Final[int] = 2
# TODO: Add validation for parameter building
# e.g. actually build the parameters

type YieldConf = SimpleYieldConf | CompositeYieldConf
# ------------------------------
class SimpleYieldConf(BaseModel, frozen = True):            # Tested
    '''
    Class representing configuration for yields
    '''
    val : float
    min : float
    max : float
    fix : bool  = False
    # ----------------------------------
    @model_validator(mode = 'after')
    def check_bounds(self) -> Self:
        if not (self.min < self.val < self.max):
            raise ValueError(f'Invalid bounds: {self}')

        return self
# ------------------------------
class CompositeYieldConf(BaseModel, frozen = True):
    '''
    Class meant to represent composite yield
    '''
    kind : Literal['mul', 'dif', 'equal']
    pars : list[str]
    # ----------------------
    @model_validator(mode = 'after')
    def check_size(self) -> Self:
        if self.kind == 'equal' and len(self.pars) != 1:
            raise ValueError(f'Equality kind requires only one parameter: {self.pars}')

        if len(self.pars) < _MIN_COMPOSITE_PARS and self.kind != 'equal':
            raise ValueError(f'At least two parameters are needed, found: {self.pars}')

        if self.kind == 'dif' and len(self.pars) != _MIN_COMPOSITE_PARS:
            raise ValueError(f'Expected two parameters found: {self.pars}')

        return self
# ------------------------------
class YieldsConf(RootModel[dict[str,SimpleYieldConf | CompositeYieldConf]], frozen = True):
    '''
    Class meant to represent dictionary between
    parameter and configuration
    '''
    # --------------------
    def __iter__(self):  # type: ignore[override]
        return iter(self.root.items())
    # --------------------
    def __contains__(self, item: object) -> bool:
        return item in self.root
    # --------------------
    def __getitem__(self, key: str) -> YieldConf:
        return self.root[key]
    # --------------------
    def __setitem__(self, key: str, val : YieldConf) -> None:
        self.root[key] = val
# ------------------------------
