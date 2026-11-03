'''
Module holding YieldCalculator class
'''
import os
import itertools

from functools         import cached_property
from pathlib           import Path
from rx_common         import Brem, Block
from dmu               import LogStore
from dmu.generic       import utilities as gut
from dmu.workflow      import Cache
from pydantic          import BaseModel, model_validator
from typing            import Final, Literal, overload
from rx_common         import Component, Qsq, Trigger, Cut, Cuts, WorkingPoint
from rx_efficiencies   import Efficiency, EfficiencyGrid, EfficiencyScanner, EfficiencyScannerConf

from .yields           import Yield, YieldGrid
from rx_common         import MVAWp
from .parameter_reader import ParameterReader

_BREM    : Final[Brem] = Brem.brx12    # Will get yields in this brem category
_RESO_QSQ: Final[Qsq ] = Qsq.jpsi      # Bin used to get normalization mode efficiencies

log=LogStore.add_logger('rx_efficiencies:yield_calculator')
_ANADIR  : Final[Path] = Path(os.environ['ANADIR'])
# ----------------------------------------
class YieldCalculatorConf(BaseModel):
    '''
    Class used to hold configuration
    '''
    path : Path
    '''
    Path to directory where outputs go
    '''
    fits : str
    '''
    Name of directory containing fits to resonant mode used
    to normalize yields or rare mode through branching fraction
    '''
    grid : dict[Cuts,list[MVAWp]]
    '''
    Grid of MVA working points where yield calculation has to be made
    '''
    # --------------------
    @model_validator(mode = 'before')
    def _validate(cls, data : dict[str,str]):
        path = data['path']
        path = _ANADIR / path

        path.mkdir(parents = True, exist_ok = True)

        data['path'] = str(path)

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
                cut_obj = Cut(cut = cut, val = val.lower, var = cut.var)
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

        self.__out_path : Path | None = None
    # -------------------------------
    @overload
    def __get_eff(self, is_norm : Literal[True ]) -> Efficiency    : ...
    @overload
    def __get_eff(self, is_norm : Literal[False]) -> EfficiencyGrid: ...
    def __get_eff(self, is_norm :           bool) -> Efficiency | EfficiencyGrid:
        '''
        Parameters
        --------------
        is_norm: If true, will calculate the resonant mode efficiencies, otherwise the rare one

        Returns
        --------------
        Normalization channel efficiency or grid of rare mode efficiencies
        '''
        if is_norm:
            log.info('Calculating normalization mode efficiency')
            wps    = [self.__wp]
            sample = self.__trg.reso_jpsi_signal
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

        self.__out_path = obj.path

        return grid
    # -------------------------------
    @property
    def path(self) -> Path:
        '''
        Path to directory where output of calculations will be
        '''
        if self.__out_path is None:
            raise ValueError('Grid path not set, calculate was not called yet?')

        return self.__out_path
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
                comp    = Component.data_24,
                brem    = _BREM,
                block   = block,
                q2bin   = _RESO_QSQ,
                trigger = self.__trg,
                cmb     = MVAWp.from_wp(wp = self.__wp, is_cmb =  True),
                prc     = MVAWp.from_wp(wp = self.__wp, is_cmb = False),
            )

            val, err = meas[f'yld_{self.__trg.reso_jpsi_signal}_{_BREM}']

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
        yld_meson= yld_raw  / self.__trg.reso_jpsi_signal.brf

        yld_rare = yld_meson * self.__trg.rare_signal.brf
        yld_grid = yld_rare  * eff_grid

        return yld_grid
# ----------------------------------------
