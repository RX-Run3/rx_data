'''
Module holding classes associated to fit yields
'''
import math
import pandas as pnd

from enum              import StrEnum, auto
from gvar              import GVar, gvar, sqrt
from typing            import overload
from functools         import cached_property
from dmu               import LogStore
from dmu.generic       import Serializable, Patchable, LinkedNode
from pydantic          import RootModel, BaseModel, model_validator
from rx_common         import BranchingFraction, Component, Cuts, Trigger, WorkingPoint
from rx_efficiencies   import Efficiency, EfficiencyGrid
from contextlib        import contextmanager
from contextvars       import ContextVar

log=LogStore.add_logger('rx_efficiencies:yields')

_ALLOW_UNMATCHED : ContextVar[bool] = ContextVar('_ALLOW_UNMATCHED', default = False)
_ALLOW_NAN_YIELD : ContextVar[bool] = ContextVar('_ALLOW_NAN_YIELD', default = False)
# ......
# TODO: Yields and yield grids implement
# ......
# yield * yield
# sqrt(yield)
# yield / yield
# ......
# which all return yields. They should return something else
# ----------------------------------------
class _Operator(StrEnum):
    '''
    Class representing binary operation
    '''
    prod = auto()
    div  = auto()
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
    @cached_property
    def ndim(self) -> int:
        '''
        Number of cuts in working point
        '''
        return len(self.wp.root)
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
    def __check_wpt(self, obj : 'Yield | Efficiency | BranchingFraction', operator : _Operator) -> WorkingPoint:
        '''
        Checks that working points for yield and efficiency are the same

        Parameters
        ---------------
        obj     : Yield efficiency or BranchingFraction
        operator: Represents binary operation between this object and `obj`

        Returns
        ---------------
        Working point that will be used in resulting yield
        '''
        if isinstance(obj, BranchingFraction):
            return self.wp

        if operator == _Operator.div:
            # Yield / eff = Yield before cuts
            if isinstance(obj, Efficiency) and self.wp == obj.wp:
                return WorkingPoint(root = [])

            # Yield / yield = object at same wp
            if isinstance(obj,      Yield) and self.wp == obj.wp:
                return self.wp

            log.error(f'Other : {obj.wp} ')
            log.error(f'Yield : {self.wp}')

            raise ValueError('Working points differ')

        if isinstance(obj, Yield):
            raise ValueError('Raise cannot multiply yields')

        # yield * efficiency = yield at efficiency wp
        return obj.wp.extend(self.wp)
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

        wp  = self.__check_wpt(obj = other, operator = _Operator.prod)
        val = self.val * other.val
        var = (self.val * other.err) ** 2 + (self.err * other.val) ** 2
        err = math.sqrt(var)

        return Yield(val = val, err = err, wp = wp)
    # ----------------------------------------
    def __rmul__(self, other : Efficiency) -> 'Yield':
        return self.__mul__(other)
    # ----------------------------------------
    def __truediv__(self, other : 'Yield | Efficiency | BranchingFraction') -> 'Yield':
        '''
        Parameters
        --------------
        other: Object representing efficiency, branching fraction or yield

        Returns
        --------------
        Object representing ratio yield and efficiency
        errors are propagated without correlation
        '''
        wp  = self.__check_wpt(obj = other, operator = _Operator.div)
        val = self.val / other.val
        rat = (self.err / self.val) ** 2 + (other.err / other.val) ** 2
        err = val * math.sqrt(rat)

        return Yield(val = val, err = err, wp = wp)
    # ----------------------------------------
    def __add__(self, other : 'Yield') -> 'Yield':
        if self.wp != other.wp:
            raise ValueError(f'Cannot add yields at different working points: {self.wp} != {other.wp}')

        var = self.gauss + other.gauss

        return Yield(val = var.mean, err = var.sdev, wp = self.wp)
    # ----------------------------------------
    def __sub__(self, other : 'Yield') -> 'Yield':
        if self.wp != other.wp:
            log.error(self.wp)
            log.error(other.wp)
            raise ValueError('Cannot add yields at different working points')

        if self.val < other.val:
            log.debug(f'Found non-positive difference: {self.val} - {other.val}')
            return Yield.nan(wp = self.wp)

        res = self.gauss - other.gauss
        yld = Yield(val = res.mean, err = res.sdev, wp = self.wp)

        return yld
    # ----------------------------------------
    @property
    def gauss(self) -> GVar:
        '''
        Gaussian random variable version of current yield
        '''
        return gvar(self.val, self.err)
    # ----------------------------------------
    @property
    def sqrt(self) -> 'Yield':
        '''
        Square root of current object
        '''
        var = sqrt(self.gauss)

        return Yield(val = var.mean, err = var.sdev, wp = self.wp)
    # ----------------------------------------
    @classmethod
    def nan(cls, wp : WorkingPoint) -> 'Yield':
        '''
        Placeholder yield, if no valid yield found
        but with defined working point
        '''
        with cls.allow_nan():
            yld = Yield(val = math.nan, err = 0, wp = wp)

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
    # ---------------------------------
    @classmethod
    def from_linked_node(
        cls,
        wp    : WorkingPoint,
        lnode : LinkedNode) -> 'Yield':
        '''
        Parameters
        ---------------
        lnode: Linked node
        wp   : Working point used as template, cut values will be replaced
               with location of linked node
        '''
        gaus = lnode.gauss
        if gaus is None:
            raise ValueError(f'Invalid linked node: {lnode}')

        new_wp  = wp.clone(values = list(lnode.coordinates))
        node    = cls(
            val = gaus.mean,
            err = gaus.sdev,
            wp  = new_wp)

        return node
# ----------------------------------------
class YieldGrid(Serializable, Patchable, RootModel[list[Yield]], frozen = True):
    '''
    Class meant to represent a collection of yields
    '''
    # ---------------------
    @model_validator(mode = 'after')
    def _validate(self) -> 'YieldGrid':
        if self.size == 0:
            raise ValueError('Empty grid found')

        dims : set[int] = { elm.ndim for elm in self.root }

        if len(dims) != 1:
            raise ValueError(f'Found elements with different dimentions in grid: {dims}')

        return self
    # ---------------------
    def __add__(self, other : 'YieldGrid') -> 'YieldGrid':
        total : list[Yield] = []
        for first in self.root:
            fall_back = Yield.nan(wp = first.wp) if _ALLOW_UNMATCHED.get() else None
            second    = other.at(first.wp, fall_back = fall_back)
            total.append(first + second)

        return YieldGrid(root = total)
    # ---------------------
    def __sub__(self, other : 'YieldGrid') -> 'YieldGrid':
        total : list[Yield] = []

        nnans = 0
        for first in self.root:
            second = other.at(wp = first.wp, fall_back = Yield.nan(wp = first.wp))
            diff   = first - second
            if math.isnan(diff.val):
                log.debug(first.wp)
                nnans += 1

            log.debug(diff)
            total.append(diff)

        if nnans > 0:
            log.warning(f'Found {nnans}/{self.size} NaNs')

        return YieldGrid(root = total)
    # ---------------------
    def __truediv__(self, other : 'YieldGrid') -> 'YieldGrid':
        yields : list[Yield] = []
        nnans = 0
        for num in self.root:
            den   = other.at(wp = num.wp, fall_back = Yield.nan(wp = num.wp))
            if math.isnan(den.val):
                ratio = Yield.nan(wp = num.wp)
                nnans+= 1
            else:
                ratio = num / den

            yields.append(ratio)

        if nnans:
            log.warning(f'Found {nnans}/{self.size} NaNs')

        return YieldGrid(root = yields)
    # ---------------------
    @property
    def sqrt(self) -> 'YieldGrid':
        '''
        Takes square root of argument grid
        '''
        new_data = [ yld.sqrt for yld in self.root ]

        return YieldGrid(root = new_data)
    # ---------------------------------
    @classmethod
    def allow_unmatched(cls):
        '''
        Inside this context operations between grids do not need to have matching working points
        '''
        token = _ALLOW_UNMATCHED.set(True)
        @contextmanager
        def _context():
            try:
                yield
            finally:
                _ALLOW_UNMATCHED.reset(token)

        return _context()
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
    def patched(self) -> 'YieldGrid':
        '''
        Patched version of current grid
        '''
        node_data = self.patch_yields(nodes = self.root)

        patch_yields : list[Yield] = []
        wp = self.root[0].wp
        for lnode in node_data:
            node = Yield.from_linked_node(lnode = lnode, wp = wp)
            patch_yields.append(node)

        return YieldGrid(root = patch_yields + self.root)
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
