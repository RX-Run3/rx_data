import os
import copy

from functools   import cached_property, lru_cache
from dmu         import LogStore
from dmu.stats   import Model, ZFitPlotterConf, zfit
from dmu.stats   import utilities as sut
from dmu.generic import utilities as gut
from dmu.generic import hashing
from typing      import Final, Self
from pathlib     import Path
from dmu.stats   import FitConf
from pydantic    import BaseModel, RootModel, model_validator
from rx_common   import Component, Project, Qsq

log = LogStore.add_logger('rx_hqm:config')

_NONE_VAR : Final[str] = 'none' # Name of variable when not binning
zpar = zfit.Parameter
zpdf = zfit.pdf.BasePDF
# -------------------------------------------------------------------
class ParamConf(RootModel[dict[str,tuple[float,float,float]]], frozen = True):
    '''
    Configuration for parameters used in fits to J/psi and psi2S bins
    '''
    # -------------------
    def set_scale(self, fr : zpdf, pr : zpdf, qsq : Qsq) -> None:
        '''
        Calculates ratio of fully reco / part reco efficiencies due to
        mass window and uses it to set the scale value

        Parameters
        -----------------
        fr/pr: PDF for fully/(part) reco fit component
        qsq  : q2-bin where components will be used
        '''
        eff_fr = self.__get_eff(pdf = fr, is_part_reco = False)
        eff_pr = self.__get_eff(pdf = pr, is_part_reco =  True)
        value  = eff_fr / eff_pr

        log.debug(f'Scale for {qsq} bin: {value:.3f}')

        scale= self.get_scale(qsq = qsq)
        scale.set_value(value)
        scale.floating = False
    # -------------------
    def __get_eff(self, pdf : zpdf, is_part_reco : bool) -> float:
        '''
        Parameters
        ---------------
        pdf         : PDF
        is_part_reco: True if part reco, false if fully reco

        Returns
        ---------------
        Efficiency due to mass cut associated to normalization range
        with respect to observable range
        '''
        obs = pdf.space
        nrm = pdf.norm

        if not isinstance(nrm, zfit.Space):
            raise ValueError(f'No normalization found for: {pdf.name}')

        lower_all, upper_all = sut.range_from_obs(obs = obs)
        lower_cut, upper_cut = sut.range_from_obs(obs = nrm)

        if lower_all >= lower_cut:
            log.error(obs)
            log.error(nrm)
            raise ValueError(f'For {pdf.name}, all lower range is not lower than fit lower: {lower_all} >= {lower_cut}')

        if upper_all <  upper_cut:
            log.error(f'Observable   : {obs}')
            log.error(f'Normalization: {nrm}')
            raise ValueError(f'For {pdf.name}, all upper range is lower than fit upper: {upper_all} < {upper_cut}')

        integral = pdf.integrate(limits = (lower_all, upper_all)).numpy()
        area     = float(integral)
        eff      = 1 / area

        log.debug(f'Efficiency for {pdf.name}: {eff:.3f}')
        if eff == 1 and not is_part_reco:
            return eff

        if eff >= 1:
            raise ValueError(f'Efficiency of mass cut for {pdf.name} is above unity: {eff:.3f}')

        return eff
    # -------------------
    @lru_cache(maxsize = 5)
    def get_ratio(self, qsq : Qsq) -> zpar:
        '''
        Parameters
        --------------
        qsq: q2-bin

        Returns
        --------------
        Ratio of part reconstructed and fully reconstructed candidates in passed bin
        '''
        match qsq:
            case Qsq.jpsi:
                return self._get_parameter(name = 'rat_jpsi')
            case Qsq.psi2:
                return self._get_parameter(name = 'rat_psi2')
            case _:
                raise ValueError(f'Invalid bin: {qsq}')
    # -------------------
    @lru_cache(maxsize = 5)
    def get_scale(self, qsq : Qsq) -> zpar:
        '''
        Parameters
        --------------
        qsq: q2-bin

        Returns
        --------------
        Parameter meant to symbolize ratio of efficiencies
        '''
        match qsq:
            case Qsq.jpsi:
                return self._get_parameter(name = 'scl_jpsi')
            case Qsq.psi2:
                return self._get_parameter(name = 'scl_psi2')
            case _:
                raise ValueError(f'Invalid bin: {qsq}')
    # -------------------
    @lru_cache(maxsize = 5)
    def get_part_reco_yield(
        self,
        qsq_comp : Qsq,
        qsq_bin  : Qsq) -> zpar:
        '''
        Parameters
        ----------------
        qsq_comp : q2-bin associated to decays whose yield is retrieved
        qsq_bin  : q2-bin where those decays live

        Returns
        ----------------
        Associated part-reco component's yield. E.g. Yield of Jpsi -> ee component
        in psi2S bin: (jpsi, psi2s)
        '''
        if qsq_comp == Qsq.jpsi and qsq_bin == Qsq.jpsi:
            return self._get_parameter(name = 'npr_jj')

        if qsq_comp == Qsq.psi2 and qsq_bin == Qsq.jpsi:
            return self._get_parameter(name = 'npr_pj')

        if qsq_comp == Qsq.jpsi and qsq_bin == Qsq.psi2:
            return self._get_parameter(name = 'npr_jp')

        if qsq_comp == Qsq.psi2 and qsq_bin == Qsq.psi2:
            return self._get_parameter(name = 'npr_pp')

        raise ValueError(f'Invalid q2-bins: {qsq_comp}/{qsq_bin}')
    # -------------------
    def __hash__(self) -> int:
        return hashing.hash_object(obj = self.root, as_int = True)
    # -------------------
    def _get_parameter(self, name : str) -> zpar:
        '''
        Retturns zfit parameter given name
        '''
        val, lower, upper = self.root[name]

        return zfit.param.Parameter(name, val, lower, upper)
# -------------------------------------------------------------------
class ObsConf(BaseModel, frozen = True):
    '''
    Class meant to configure observables needed in
    transfer function calculation
    '''
    name       : str
    kdem_range : tuple[float,float]
    '''
    Range used to build KDE PDFs, wider than fit/normalization observable
    needed to use all information available in dataset and avoid edge effects
    '''
    mass_range : tuple[float,float]
    tran_range : tuple[float,float]
    #---------------------------------
    @property
    def kde_obs(self) -> zfit.Space:
        '''
        Observable that will be fitted for source datasets
        '''
        return zfit.Space(self.name, limits = self.kdem_range)
    #---------------------------------
    @property
    def fit_obs(self) -> zfit.Space:
        '''
        Observable that will be fitted for target datasets
        '''
        return zfit.Space(self.name, limits = self.mass_range)
    #---------------------------------
    @property
    def trn_obs(self) -> zfit.Space:
        '''
        Observable for transfer function
        '''
        return zfit.Space(self.name, limits = self.tran_range)
# -------------------------------------------------------------------
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
# -------------------------------------------------------------------
class _Conf(BaseModel, frozen = True):
    '''
    Base class for all configuration classes
    '''
    bandwidth  : int
    observable : ObsConf
    binning    : BinningConf
    fft_npt    : int
    '''
    Number of points used to sample KDE before doing convolution with
    Fast Fourier Transform
    '''
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
        subdir  : str | None = None,
        fname   : str | None = None) -> Path:
        '''
        Function will make a path and return it.

        Parameters
        -----------------
        kind   : Name of directory meant to sybolize what data will be stored there, e.g. fits, trfc
        project: E.g. rk, rkst
        fname  : Optional, file name, e.g. data.json
        subdir : Optional, subirectory path, e.g. block_1/

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

        dir_path = anadir / f'DB/hqm/{kind}/latest/{binning}/{project}'
        if subdir:
            dir_path = dir_path / subdir

        dir_path.mkdir(parents = True, exist_ok = True)

        if fname is None:
            return dir_path

        return dir_path / fname
# -------------------------------------------------------------------
class TransferFunctionMakerConf(_Conf, frozen = True):
    '''
    Configuration controlling how transfer function is built
    '''
    fits      : FitConf
    plots     : ZFitPlotterConf
    source    : Qsq
    target    : Qsq
    models    : list[Model]
    components: tuple[Component, Component]
    # -----------------------------------------------
    @cached_property
    def source_component(self) -> Component:
        '''
        Component needed as starting point of transfer function
        '''
        value, _ = self.components

        return value
    # -----------------------------------------------
    @cached_property
    def target_component(self) -> Component:
        '''
        Component needed as ending point of transfer function
        '''
        _, value = self.components

        return value
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
        project : Project,
        source  : Qsq,
        target  : Qsq) -> 'TransferFunctionMakerConf':

        cfgs = cls.load(
            project  = project,
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
        project : Project,
        source  : Qsq,
        target  : Qsq) -> list['TransferFunctionMakerConf']:
        '''
        Parameters
        ---------------
        variable : Variable to bin, none for unbinned
        project  : I.e. rk or rkst
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
        cfg['components'] = trf_data['models'][project][source]

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
# -------------------------------------------------------------------
class CCbarRatioCalculatorConf(_Conf, frozen = True):
    '''
    Class meant to configure CCbarRatioCalculator
    '''
    sb_mass : float
    '''
    Mass cut on DTF mass, needed to isolate part reco candidates
    in muon dataset
    '''
    parameters : ParamConf
    '''
    Configuration for parameters in fits to J/psi and psi2S bins
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
        rtc_data = gut.load_data(package = 'hqm_data', fpath = 'config/ratc.yaml')

        rtc_data['observable'] = trf_data['observable']
        bin_cfgs = cls._get_bin_cfgs(variable = variable)

        cfgs : list['CCbarRatioCalculatorConf'] = []
        for bin_data in bin_cfgs:
            this_data            = copy.deepcopy(rtc_data)
            this_data['binning'] = bin_data

            cfgs.append(cls(**this_data))

        return cfgs
#-------------------------------------------------------------------
