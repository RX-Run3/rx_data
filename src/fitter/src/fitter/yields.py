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
from contextlib        import contextmanager
from contextvars       import ContextVar

log=LogStore.add_logger('rx_efficiencies:yields')

_ALLOW_NAN_YIELD : ContextVar[bool] = ContextVar('_ALLOW_NAN_YIELD', default = False) 
# ----------------------------------------
class ProjectConf(BaseModel):
    '''
    Class holding configuration
    '''
    trigger       : Trigger
    signal        : Component
    normalization : Component
# ----------------------------------------
class Yield(BaseModel, frozen = True):
    '''
    Class used to represent yields
    '''
    val : float
    err : float
    wp  : WorkingPoint
    # ----------------------------------------
    @model_validator(mode = 'after')
    def _validate(self) -> 'Yield':
        allow_nan = _ALLOW_NAN_YIELD.get()
        has_nans  = math.isnan(self.val) or math.isnan(self.err)

        if not allow_nan and has_nans:
            raise ValueError(f'Yield contains NaNs: {self}')

        if self.err < 0.:
            raise ValueError(f'Yield error cannot be zero or negative, found: {self.err}')

        if self.val < 0.:
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
    @classmethod
    def nan(cls) -> 'Yield':
        '''
        Placeholder yield, if no valid yield found
        '''
        wp = WorkingPoint(root = [])
        with cls.allow_nan():
            yld = Yield(val = math.nan, err = 0, wp = wp)

        return yld
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
    def __sub__(self, other : 'Yield') -> 'Yield':
        if self.wp != other.wp:
            log.error(self.wp)
            log.error(other.wp)
            raise ValueError('Cannot add yields at different working points')

        val = self.val      - other.val
        # NOTE: Negative yields are not allowed, make it zero
        # This is likely a statistical fluctuation
        if val < 0:
            log.debug(f'Found non-positive difference: {self.val} - {other.val}')
            val = math.nan

        var = self.err ** 2 + other.err ** 2
        err = math.sqrt(var)

        yld = Yield(val = val, err = err, wp = self.wp)

        return yld
    # ----------------------------------------
    @classmethod
    def null(cls, wp : WorkingPoint) -> 'Yield':
        '''
        Yield representing no entries
        '''
        return cls(val = 1e-3, err = 1e-3, wp = wp)
    # ---------------------------------
    @classmethod
    def allow_nan(cls):
        '''
        Inside this context, Yield will accept NaN values
        '''
        token = _ALLOW_NAN_YIELD.set(True)
        @contextmanager
        def _context():
            try:
                yield
            finally:
                _ALLOW_NAN_YIELD.reset(token)

        return _context()
# ----------------------------------------
class YieldGrid(RootModel[list[Yield]], frozen = True):
    '''
    Class meant to represent a collection of yields
    '''
    # ---------------------
    def __add__(self, other : 'YieldGrid') -> 'YieldGrid':
        if self.size != other.size:
            raise ValueError(f'Cannot add grids with different sizes: {self.size} != {other.size}')

        total : list[Yield] = []
        for first, second in zip(self.root, other.root, strict=True):
            total.append(first + second)

        return YieldGrid(root = total)
    # ---------------------
    def __sub__(self, other : 'YieldGrid') -> 'YieldGrid':
        total : list[Yield] = []

        nnans = 0
        for first in self.root:
            second = other.at(wp = first.wp, fall_back = Yield.nan())
            diff   = first - second
            if math.isnan(diff.val):
                log.info(first.wp)
                nnans += 1

            log.debug(diff)
            total.append(diff)

        if nnans > 0:
            log.warning(f'Found {nnans}/{self.size} NaNs')

        return YieldGrid(root = total)
    # ---------------------
    @cached_property
    def __mapping(self) -> dict[int,Yield]:
        yields = { hash(yld.wp) : yld for yld in self.root }

        if len(yields) != self.size:
            raise ValueError(f'Hashes in yield grid are non-unique: {len(yields)} < {self.size}')

        return yields
    # ---------------------
    def at(
        self, 
        wp        : WorkingPoint, 
        fall_back : Yield | None) -> Yield:
        '''
        Parameters
        -------------
        wp       : Working point at which yield will be searched in current grid
        fall_back: If yield not found at `wp`, pick this value

        Returns
        -------------
        Yield
        '''
        hsh = hash(wp)
        if hsh in self.__mapping:
            return self.__mapping[hsh]

        if fall_back:
            return fall_back

        raise ValueError(f'No yield found at WP: {wp}')
    # ---------------------
    @property
    def size(self):
        '''
        Number of yields in grid
        '''
        return len(self.root)
    # ---------------------
    @cached_property
    def df(self) -> pnd.DataFrame:
        '''
        Dataframe with yield information
        '''
        rows : list[dict[str,float]] = [ yld.row for yld in self.root ]

        return pnd.DataFrame(rows)
# ----------------------------------------
