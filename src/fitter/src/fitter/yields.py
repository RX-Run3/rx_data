'''
Module holding classes associated to fit yields
'''
import math
import pandas as pnd

from typing            import overload
from functools         import cached_property
from dmu               import LogStore
from pydantic          import RootModel, BaseModel, model_validator
from rx_common         import BranchingFraction, Component, Cuts, Trigger, WorkingPoint
from rx_efficiencies   import Efficiency, EfficiencyGrid

log=LogStore.add_logger('rx_efficiencies:yields')
# ----------------------------------------
class ProjectConf(BaseModel):
    '''
    Class holding configuration
    '''
    trigger       : Trigger
    signal        : Component
    normalization : Component
# ----------------------------------------
class Yield(BaseModel):
    '''
    Class used to represent yields
    '''
    val : float
    err : float
    wp  : WorkingPoint
    # ----------------------------------------
    @model_validator(mode = 'after')
    def _validate(self) -> 'Yield':
        if math.isnan(self.val) or math.isnan(self.err):
            raise ValueError(f'Yield contains NaNs: {self}')

        if self.err <= 0.:
            raise ValueError(f'Yield error cannot be zero or negative, found: {self.err}')

        if self.val < 0 :
            raise ValueError(f'Yield is negative: {self.val}')

        return self
    # ----------------------------------------
    @cached_property
    def row(self) -> dict[str,float]:
        '''
        Data associated to yield meant to go in row in dataframe
        '''
        cmb = self.wp.get_val(cut = Cuts.cmb)
        prc = self.wp.get_val(cut = Cuts.prc)

        return {'yld' : self.val, 'err' : self.err, 'cmb' : cmb, 'prc' : prc}
    # ----------------------------------------
    def __str__(self) -> str:
        msg = f'''
        Value: {self.val:.3g}
        Error: {self.err:.3g}
        '''

        return msg
    # ----------------------------------------
    def __check_wpt(self, eff : Efficiency, is_ratio : bool) -> WorkingPoint:
        '''
        Checks that working points for yield and efficiency are the same

        Parameters
        ---------------
        eff     : Efficiency object
        is_ratio: True if the check is part of a division yld / eff, false for yld * eff

        Returns
        ---------------
        Working point that will be used in resulting yield
        '''
        if     is_ratio and self.wp == eff.wp:
            return WorkingPoint(root = []) 

        if not is_ratio and self.wp.is_empty:
            return eff.wp

        log.error(f'Efficiency: {eff.wp} ')
        log.error(f'Yield     : {self.wp}')

        raise ValueError('Working points differ')
    # ----------------------------------------
    @overload
    def __mul__(self, other : BranchingFraction                              ) -> 'Yield': ...
    @overload
    def __mul__(self, other : EfficiencyGrid                                 ) -> 'YieldGrid': ...
    @overload
    def __mul__(self, other : Efficiency                                     ) -> 'Yield': ...
    def __mul__(self, other : BranchingFraction | Efficiency | EfficiencyGrid) -> 'Yield|YieldGrid':
        '''
        Parameters
        --------------
        other: Object representing efficiency or collection of efficiencies

        Returns
        --------------
        Object representing product of efficiency(grid) and yield
        errors are propagated without correlation
        '''
        if isinstance(other, EfficiencyGrid):
            yields = [ self * effi for effi in other.root ]
            return YieldGrid(root = yields)

        if isinstance(other, Efficiency):
            wp  = self.__check_wpt(eff = other, is_ratio = False)
        else:
            wp  = self.wp

        val = self.val * other.val
        var = (self.val * other.err) ** 2 + (self.err * other.val) ** 2
        err = math.sqrt(var)

        return Yield(val = val, err = err, wp = wp)
    # ----------------------------------------
    def __rmul__(self, other : Efficiency) -> 'Yield':
        return self.__mul__(other)
    # ----------------------------------------
    def __truediv__(self, other : Efficiency | BranchingFraction) -> 'Yield':
        '''
        Parameters
        --------------
        other: Object representing efficiency

        Returns
        --------------
        Object representing ratio yield and efficiency
        errors are propagated without correlation
        '''
        if isinstance(other, Efficiency):
            wp = self.__check_wpt(eff = other, is_ratio = True)
        else:
            wp = self.wp

        val = self.val / other.val
        rat = (self.err / self.val) ** 2 + (other.err / other.val) ** 2
        err = val * math.sqrt(rat)

        return Yield(val = val, err = err, wp = wp)
    # ----------------------------------------
    def __add__(self, other : 'Yield') -> 'Yield':
        if self.wp != other.wp:
            raise ValueError(f'Cannot add yields at different working points: {self.wp} != {other.wp}')

        val = self.val      + other.val
        var = self.err ** 2 + other.err ** 2
        err = math.sqrt(var)

        return Yield(val = val, err = err, wp = self.wp)
    # ----------------------------------------
    @classmethod
    def null(cls, wp : WorkingPoint) -> 'Yield':
        '''
        Yield representing no entries
        '''
        return cls(val = 1e-3, err = 1e-3, wp = wp)
# ----------------------------------------
class YieldGrid(RootModel[list[Yield]]):
    '''
    Class meant to represent a collection of yields
    '''
    # ---------------------
    @cached_property
    def df(self) -> pnd.DataFrame:
        '''
        Dataframe with yield information
        '''
        rows : list[dict[str,float]] = [ yld.row for yld in self.root ]

        return pnd.DataFrame(rows)
# ----------------------------------------
