import os
import copy

from dmu         import LogStore
from dmu.stats   import Model, ZFitPlotterConf, zfit
from dmu.generic import utilities as gut
from typing      import Final, Self
from pathlib     import Path
from dmu.stats   import FitConf
from pydantic    import BaseModel, model_validator
from rx_common   import Project, Qsq

log = LogStore.add_logger('rx_hqm:config')

_NONE_VAR : Final[str] = 'none' # Name of variable when not binning
#-------------------------------------------------------------------
class ObsConf(BaseModel, frozen = True):
    '''
    Class meant to configure observables needed in
    transfer function calculation
    '''
    name       : str
    mass_range : tuple[float,float]
    tran_range : tuple[float,float]
    #---------------------------------
    @property
    def fit_obs(self) -> zfit.Space:
        '''
        Observable that will be fitted for source and target datasets
        '''
        return zfit.Space(self.name, limits = self.mass_range)
    #---------------------------------
    @property
    def trn_obs(self) -> zfit.Space:
        '''
        Observable for transfer function 
        '''
        return zfit.Space(self.name, limits = self.tran_range)
#-------------------------------------------------------------------
class BinningConf(BaseModel, frozen = True):
    '''
    Config describing 
    '''
    variable : str
    '''
    Variable to cut on, e.g. B_PT
    '''

    bin   : int
    '''
    Index of bin, needed to pick up cut
    '''

    bins  : list[tuple[float,float]]
    '''
    Expression defining cut
    '''
    # ------------------------
    @property
    def cut(self) -> str:
        '''
        Cut associated to current bin, meant to be used
        by RDataFrame::Filter, uses semi-open range [lower, upper)
        '''
        if self.variable == _NONE_VAR:
            return 'true'

        lower, upper = self.bins[self.bin]

        return f'({self.variable} >= {lower}) && ({self.variable} < {upper})'
    # ------------------------
    @property
    def is_unbinned(self) -> bool:
        '''
        True if unbinned
        '''
        return self.variable == _NONE_VAR
    # ------------------------
    @model_validator(mode = 'after')
    def _validate(self) -> Self:
        ncut = len(self.bins)
        if self.bin < 0:
            raise ValueError(f'Non-positive bin found: {self.bin}')

        if ncut == 0:
            raise ValueError('Found no cuts')

        if self.variable == _NONE_VAR:
            if ncut != 1:
                raise ValueError('Unbinned case requires one bin')

        if ncut <= self.bin:
            raise ValueError(f'Bin index {self.bin} incompatible with number of bins {ncut}')

        return self
    # ------------------------
    @property
    def prefix(self) -> str:
        '''
        String used to identify transfer function, e.g. brem_001
        '''
        if self.is_unbinned:
            return 'unbinned'

        return f'{self.variable}_{self.bin:03d}'
#-------------------------------------------------------------------
class _Conf(BaseModel, frozen = True):
    '''
    Base class for all configuration classes
    '''
    observable : ObsConf
    binning    : BinningConf
    # ----------------------------------
    def __str__(self):
        return f'''
        -----------------
        Observable
        -----------------
        {self.observable}

        -----------------
        Binning 
        -----------------
        {self.binning}
        '''
    # -----------------------------------------------
    @classmethod
    def _get_bin_cfgs(cls, variable : str) -> list[dict]:
        '''
        Parameters
        ----------------
        variable: Name of variable used for binning

        Returns
        ----------------
        List of dictionaries with data used to build BinningConf
        '''
        bin_data = gut.load_data(package = 'hqm_data', fpath = 'config/binning.yaml')
        nbin = len(bin_data[variable])
        if nbin == 0:
            raise ValueError(f'No bins found for variable: {variable}')

        bin_cfgs : list[dict] = []
        for ibin in range(nbin):
            cfg_bin             = dict()
            cfg_bin['variable'] = variable 
            cfg_bin['bin'     ] = ibin
            cfg_bin['bins'    ] = bin_data[variable]

            bin_cfgs.append(cfg_bin)

        return bin_cfgs
    # -----------------------------------------------
    def make_path(
        self,
        *,
        kind    : str, 
        project : Project,
        fname   : str | None = None) -> Path:
        '''
        Function will make a path and return it. 

        Parameters 
        -----------------
        kind   : Name of directory meant to sybolize what data will be stored there, e.g. fits, trfc
        project: E.g. rk, rkst
        fname  : Optional, file name, e.g. data.json

        Returns
        -----------------
        Path to either file or directory
        '''
        if self.binning.is_unbinned:
            binning = 'unbinned'
        else:
            binning = f'{self.binning.variable}_{self.binning.bin:03d}'

        anadir = Path(os.environ['ANADIR'])
        log.debug(f'Using ANADIR: {anadir}')

        dir_path = anadir / f'{kind}/{binning}/{project}'
        dir_path.mkdir(parents = True, exist_ok = True)

        if fname is None:
            return dir_path

        return dir_path / fname 
#-------------------------------------------------------------------
class TransferFunctionMakerConf(_Conf, frozen = True):
    '''
    Configuration controlling how transfer function is built
    '''
    bandwidth : int
    fft_npt   : int
    fits      : FitConf
    plots     : ZFitPlotterConf
    source    : Qsq
    target    : Qsq
    models    : list[Model]
    # -----------------------------------------------
    def __str__(self):
        return f'''
        Name: {self.name}

        ----------
        Data
        ----------
        Source: {self.source}
        Target: {self.target}
        Models: {self.models}

        ----------
        Fits
        ----------
        {self.fits}

        ----------
        Plots
        ----------
        {self.plots}

        ----------
        Binning
        ----------
        {self.binning}
        '''
    # -----------------------------------------------
    @property
    def name(self) -> str:
        '''
        String meant to be used to identify PDFs, etc
        '''
        if self.binning.is_unbinned:
            binning = 'unbinned'
        else:
            binning = self.binning.prefix

        return f'{self.source}_{self.target}_{binning}'
    # -----------------------------------------------
    @classmethod
    def load_bin_cfg(
        cls, 
        bin     : int,
        variable: str,
        source  : Qsq,
        target  : Qsq) -> 'TransferFunctionMakerConf':

        cfgs = cls.load(
            source   = source,
            target   = target,
            variable = variable)

        try:
            [cfg] = [ cfg for cfg in cfgs if cfg.binning.bin == bin ]
        except Exception:
            for cfg in cfgs:
                log.info(cfg.binning.bin)
            raise ValueError(f'No configuration found for bin: {bin}')

        return cfg
    # -----------------------------------------------
    @classmethod
    def load(
        cls, 
        variable: str,
        source  : Qsq,
        target  : Qsq) -> list['TransferFunctionMakerConf']:
        '''
        Parameters
        ---------------
        variable : Variable to bin, none for unbinned 
        source   : Origin (muon) q2 bin 
        target   : Needed (electron) q2 bin

        Returns
        ---------------
        Config object
        '''
        trf_data = gut.load_data(package = 'hqm_data', fpath = 'config/transfer.yaml')
        qsq_data = trf_data['qsq']
        cfg      = dict() 

        for q2_cfg in qsq_data:
            if q2_cfg['source'] != source:
                continue

            if q2_cfg['target'] != target:
                continue

            cfg.update(q2_cfg)

        cfg['fits'      ] = trf_data['fits'       ]
        cfg['observable'] = trf_data['observable' ]
        cfg['fft_npt'   ] = trf_data['fft_npt'    ]
        cfg['bandwidth' ] = trf_data['bandwidth'  ]

        cfg['plots'].update(trf_data['plots'])
        if cfg is None:
            raise ValueError(f'Missing configuration for {source}/{target}')

        bin_cfgs = cls._get_bin_cfgs(variable = variable)

        confs : list['TransferFunctionMakerConf'] = []
        for cfg_bin in bin_cfgs:
            this_cfg = copy.deepcopy(cfg)
            this_cfg['binning'] = cfg_bin

            confs.append(cls(**this_cfg))

        return confs
    # -----------------------------------------------
    @staticmethod
    def print_config(name) -> None:
        if not hasattr(TransferFunctionMakerConf, name):
            log.error(f'Cannot find {name} in configuration')
            raise

        d_data = getattr(TransferFunctionMakerConf, name)
        log.info(80 * '-')
        log.info(f'{"Setting":<30}{"Value":<50}')
        log.info(80 * '-')
        for key, val in d_data.items():
            log.info(f'{key:<30}{val:<50}')
#-------------------------------------------------------------------
class CCbarRatioCalculatorConf(_Conf, frozen = True):
    '''
    Class meant to configure CCbarRatioCalculator
    '''
    # ----------------------------------
    @classmethod
    def load(cls, variable: str) -> list['CCbarRatioCalculatorConf']:
        '''
        Parameters
        ----------------
        variable: Variable to bin in, none for unbinned

        Returns
        ----------------
        List of configuration objects
        '''
        trf_data = gut.load_data(package = 'hqm_data', fpath = 'config/transfer.yaml')

        data               = dict()
        data['observable'] = trf_data['observable']
        bin_cfgs = cls._get_bin_cfgs(variable = variable)

        cfgs : list['CCbarRatioCalculatorConf'] = []
        for bin_data in bin_cfgs:
            this_data            = copy.deepcopy(data)
            this_data['binning'] = bin_data

            cfgs.append(cls(**this_data))

        return cfgs
#-------------------------------------------------------------------
