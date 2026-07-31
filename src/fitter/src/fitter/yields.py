'''
Module holding classes associated to fit yields
'''
import os
import math
import pandas as pnd
import itertools

from pathlib           import Path
from typing            import Final, Literal, overload
from functools         import cached_property
from dmu               import LogStore
from dmu.generic       import utilities as gut
from dmu.workflow      import Cache
from pydantic          import RootModel, BaseModel, model_validator
from rx_common         import Component, Cut, Cuts, Qsq, Trigger, WorkingPoint
from rx_common         import Brem, Block
from rx_efficiencies   import Efficiency, EfficiencyGrid, EfficiencyScanner, EfficiencyScannerConf

from .mva_conf         import MVAWp
from .parameter_reader import ParameterReader

log=LogStore.add_logger('rx_efficiencies:yields')

_ANADIR  : Final[Path] = Path(os.environ['ANADIR'])
_BREM    : Final[Brem] = Brem.brx12    # Will get yields in this brem category
_RESO_QSQ: Final[Qsq ] = Qsq.jpsi      # Bin used to get normalization mode efficiencies
# ----------------------------------------
class ProjectConf(BaseModel):
    '''
    Class holding configuration
    '''
    trigger       : Trigger
    signal        : Component
    normalization : Component
# ----------------------------------------
class YieldCalculatorConf(BaseModel):
    '''
    Class used to hold configuration
    '''
    path : Path
    fits : str
    grid : dict[Cuts,list[float]]
    # --------------------
    @model_validator(mode = 'before')
    def _validate(cls, data):
        path = data['path']
        path = _ANADIR / path

        path.mkdir(parents = True, exist_ok = True)

        data['path'] = path

        return data
    # --------------------
    @cached_property
    def wps(self) -> list[WorkingPoint]:
        '''
        List of objects representing cuts
        '''
        all_cuts : list[list[Cut]] = []
        for cut, vals in self.grid.items():
            cuts : list[Cut] = []
            for val in vals:
                cut_obj = Cut(cut = cut, val = val, var = cut.var)
                cuts.append(cut_obj)

            all_cuts.append(cuts)

        combinations = list(itertools.product(*all_cuts))

        values = [WorkingPoint(root = list(combination)) for combination in combinations ]

        return values
    # --------------------
    @classmethod
    def from_name(cls, name : str) -> 'YieldCalculatorConf':
        '''
        Parameters
        -----------------
        name: string identifying file holding configuration, e.g. rare 

        Returns
        -----------------
        Configuration object
        '''
        data = gut.load_data(
            package = 'fitter_data', 
            fpath   = f'yields/{name}.yaml')

        return cls(**data)
# ----------------------------------------
class Yield(BaseModel):
    '''
    Class used to represent yields
    '''
    val : float
    err : float
    wp  : WorkingPoint
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
    def __mul__(self, other : EfficiencyGrid             ) -> 'YieldGrid': ...
    @overload
    def __mul__(self, other : Efficiency                 ) -> 'Yield': ...
    def __mul__(self, other : Efficiency | EfficiencyGrid) -> 'Yield|YieldGrid':
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

        wp  = self.__check_wpt(eff = other, is_ratio = False)
        val = self.val * other.val
        var = (self.val * other.err) ** 2 + (self.err * other.val) ** 2
        err = math.sqrt(var)

        return Yield(val = val, err = err, wp = wp)
    # ----------------------------------------
    def __rmul__(self, other : Efficiency) -> 'Yield':
        return self.__mul__(other)
    # ----------------------------------------
    def __truediv__(self, other : Efficiency) -> 'Yield':
        '''
        Parameters
        --------------
        other: Object representing efficiency

        Returns
        --------------
        Object representing ratio yield and efficiency
        errors are propagated without correlation
        '''
        wp  = self.__check_wpt(eff = other, is_ratio = True)
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
    @model_validator(mode = 'after')
    def _validate(self) -> 'Yield':
        if self.err <= 0.:
            raise ValueError(f'Yield error cannot be zero or negative, found: {self.err}')

        return self
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
class YieldCalculator:
    '''
    Class used to calculate expected yields based
    on resonant mode yields and efficiencies
    '''
    # -------------------------------
    def __init__(
        self, 
        name    : str, 
        wp      : WorkingPoint,
        q2bin   : Qsq,
        trigger : Trigger):
        '''
        Parameters
        ---------------
        name   : Name of configuration file, e.g. rare
        wp     : Working point used for the normalization yield/efficiency
        project: E.g. rk
        q2bin  : E.g. low
        '''
        self.__cfg = YieldCalculatorConf.from_name(name = name) 
        self.__trg = trigger 
        self.__qsq = q2bin
        self.__wp  = wp
    # -------------------------------
    @overload
    def __get_eff(self, is_norm : Literal[True ]) -> Efficiency    : ...
    @overload
    def __get_eff(self, is_norm : Literal[False]) -> EfficiencyGrid: ...
    def __get_eff(self, is_norm :           bool) -> Efficiency | EfficiencyGrid:
        '''
        Returns
        --------------
        Normalization channel efficiency
        '''
        if is_norm:
            log.info('Calculating normalization mode efficiency')
            wps    = [self.__wp]
            sample = self.__trg.reso_signal
            q2bin  = _RESO_QSQ
        else:
            log.info('Calculating signal mode efficiencies')
            wps    = self.__cfg.wps
            sample = self.__trg.rare_signal
            q2bin  = self.__qsq

        cfg = EfficiencyScannerConf(
            sample = sample,
            trigger= self.__trg,
            q2bin  = q2bin,
            wps    = wps)

        with Cache.cache_root(path = self.__cfg.path):
            obj  = EfficiencyScanner(cfg = cfg)
            grid = obj.run()

        if is_norm:
            return grid.root[0]

        return grid
    # -------------------------------
    def __get_yld_norm(self) -> Yield:
        '''
        Returns
        --------------
        Yield in normalization mode
        '''
        rdr = ParameterReader(name = self.__cfg.fits)

        total_yield = Yield.null(wp = self.__wp)
        for block in Block.blocks():
            meas = rdr(
                is_mc   = False,
                brem    = _BREM,
                block   = block,
                q2bin   = _RESO_QSQ,
                trigger = self.__trg,
                cmb     = MVAWp.from_wp(wp = self.__wp, is_cmb =  True),
                prc     = MVAWp.from_wp(wp = self.__wp, is_cmb = False),
            )

            val, err = meas[f'yld_{self.__trg.reso_signal}_{_BREM}']

            total_yield += Yield(val = val, err = err, wp = self.__wp)

        return total_yield
    # -------------------------------
    def calculate(self) -> YieldGrid:
        '''
        Returns
        --------------
        Yield grid, e.g. holder of yields
        '''
        eff_norm = self.__get_eff(is_norm =  True)
        eff_grid = self.__get_eff(is_norm = False)
        yld_norm = self.__get_yld_norm()

        yld_raw  = yld_norm / eff_norm
        yld_grid = yld_raw * eff_grid

        return yld_grid
# ----------------------------------------
