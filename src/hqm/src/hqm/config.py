import os

from functools   import cached_property
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

from .binning    import BinConf, BinningConf

log       = LogStore.add_logger('hqm:config')
type zpar = zfit.Parameter | zfit.ComposedParameter
type zpdf = zfit.pdf.BasePDF
type zobs = zfit.Space

_SG_VALS       : Final[tuple[float,float,float]] = 80, 10, 300 # Starting value and range for width of transfer functions
_LOWER_ALL     : Final[float]                    = 3000
_UPPER_ALL     : Final[float]                    = 7500
_CACHED_PARAMS : dict[str, zpar]                 = dict()
# -------------------------------------------------------------------
class ParamConf(RootModel[dict[str,tuple[float,float,float]]], frozen = True):
    '''
    Configuration for parameters used in fits to J/psi and psi2S bins
    '''
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
        obs                  = pdf.space
        lower_cut, upper_cut = sut.range_from_obs(obs = obs)

        if _LOWER_ALL >= lower_cut:
            log.error(obs)
            raise ValueError(f'For {pdf.name}, all lower range is not lower than fit lower: {_LOWER_ALL} >= {lower_cut}')

        if _UPPER_ALL <  upper_cut:
            log.error(f'Observable   : {obs}')
            raise ValueError(f'For {pdf.name}, all upper range is lower than fit upper: {_UPPER_ALL} < {upper_cut}')

        integral = pdf.integrate(limits = (_LOWER_ALL, _UPPER_ALL)).numpy()
        area     = float(integral)
        eff      = 1 / area

        log.debug(f'Efficiency for {pdf.name}: {eff:.3f}')
        if eff == 1 and not is_part_reco:
            return eff

        if eff >= 1:
            raise ValueError(f'Efficiency of mass cut for {pdf.name} is above unity: {eff:.3f}')

        return eff
    # -------------------
    def get_factor(
        self,
        pdf_fr  : zpdf,
        pdf_pr  : zpdf,
        qsq_src : Qsq,
        qsq_tgt : Qsq) -> zpar:
        '''
        Parameters
        --------------
        pdf_fr/pr: PDF for the part-reco/fully-reco component
        qsq_src  : q2 associated to decays, e.g. Jpsi -> ee => jpsi
        qsq_tgt  : q2 bin

        Returns
        --------------
        Factor between part reco and fully reco yields

        math::
        ratio       = npart_reco_total             / nfully_reco_total
        ratio       = (npart_reco / eff_part_reco) / (nfully_reco / eff_fully_reco)
        ratio       = (npart_reco / nfully_reco) * (eff_fully_reco / eff_part_reco)
        ratio       = (npart_reco / nfully_reco) * scale

        nfully_reco = (npart_reco / ratio) * scale
        nfully_reco = npart_reco  * (scale / ratio)
        nfully_reco = npart_reco  * fac

        fac = (eff_fully_reco / eff_part_reco) / ratio
        :::
        '''
        name  = f'fac_{qsq_src}_{qsq_tgt}'
        if name in _CACHED_PARAMS:
            return _CACHED_PARAMS[name]

        ratio = self._get_parameter(name = f'rat_{qsq_src}')
        lims  = _LOWER_ALL, _UPPER_ALL

        fr_eff = 1. / pdf_fr.integrate(limits = lims)[0]
        pr_eff = 1. / pdf_pr.integrate(limits = lims)[0]
        scale  = float(fr_eff / pr_eff)

        log.debug('-----------------------')
        log.debug(f'{qsq_src} -> {qsq_tgt}')
        log.debug('-----------------------')
        log.debug(f'Fully reco fraction: {fr_eff:g}')
        log.debug(f'Part  reco fraction: {pr_eff:g}')
        log.debug(f'Scale: {scale:g}')
        log.debug('-----------------------')

        scale = zfit.param.ConstantParameter(name = f'scl_{qsq_src}_{qsq_tgt}', value = scale)
        fac   = zfit.ComposedParameter(
            name,
            lambda params : params['scale'] / params['ratio'],
            params = {'scale' : scale, 'ratio' : ratio})

        _CACHED_PARAMS[name] = fac

        return fac
    # -------------------
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
        if name in _CACHED_PARAMS:
            return _CACHED_PARAMS[name]

        val, lower, upper = self.root[name]

        param                = zfit.param.Parameter(name, val, lower, upper)
        _CACHED_PARAMS[name] = param

        return param
# -------------------------------------------------------------------
class ObsConf(BaseModel, frozen = True):
    '''
    Class meant to configure observables needed in
    transfer function calculation
    '''
    name       : str
    wide_range : tuple[float,float]
    '''
    Range used to build KDE PDFs, wider than fit/normalization observable
    needed to use all information available in dataset and avoid edge effects
    '''
    mass_range : tuple[float,float]
    tran_range : dict[Qsq,dict[Qsq,tuple[float, float, float]]]
    #---------------------------------
    @model_validator(mode = 'after')
    def _validate(self) -> Self:
        for _, val in self.tran_range.items():
            for _, (_, min_trn, max_trn) in val.items():
                self._validate_range(min_trn, max_trn)

        return self
    #---------------------------------
    def _validate_range(self, min_trn : float, max_trn : float) -> None:
        min_fit, max_fit = self.wide_range
        fit_rng = max_fit - min_fit
        trn_rng = max_trn - min_trn

        if fit_rng <= trn_rng:
            log.error(self.wide_range)
            log.error(self.tran_range)
            raise ValueError('Fit range is shorter than transfer function range')
    #---------------------------------
    @property
    def mass_obs(self) -> zfit.Space:
        '''
        Observable meant to agree with mass range in electron channel
        '''
        return zfit.Space(self.name, limits = self.mass_range)
    #---------------------------------
    @property
    def wide_obs(self) -> zfit.Space:
        '''
        Observable using wide mass range used for:

        - Fits to KDEs to avoid edge effects
        - Fits to get PDFs meant to be convolved with wide transfer functions
        '''
        return zfit.Space(self.name, limits = self.wide_range)
# -------------------------------------------------------------------
class SerializationConf(BaseModel, frozen=True):
    '''
    Class configuring how an object should be serialized
    '''
    binning    : BinConf
    # ----------------------------------
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
        anadir = Path(os.environ['ANADIR'])
        log.debug(f'Using ANADIR: {anadir}')

        dir_path = anadir / f'DB/hqm/{kind}/latest/{self.binning.dir_path}/{project}'
        if subdir:
            dir_path = dir_path / subdir

        dir_path.mkdir(parents = True, exist_ok = True)

        if fname is None:
            return dir_path

        return dir_path / fname
# -------------------------------------------------------------------
class PDFConf(SerializationConf, frozen = True):
    '''
    Class holding information needed to build PDF
    '''
    bandwidth  : int
    observable : ObsConf
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
# -------------------------------------------------------------------
class TransferFunctionMakerConf(PDFConf, frozen = True):
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
    def trn_obs(self) -> zobs:
        '''
        Observable used to build transfer function
        '''
        _, min_val, max_val = self.observable.tran_range[self.source][self.target]
        name                = self.observable.name

        return zfit.Space(name, limits = (min_val, max_val))
    # -----------------------------------------------
    @cached_property
    def trn_vals(self) -> dict[str,tuple[float,float,float]]:
        '''
        Dictionary mapping name of parameter with values:
        initial, lower bound, upper bound
        '''
        src     = self.source
        tgt     = self.target
        mu_vals = self.observable.tran_range[src][tgt]

        return {
            'sg' : _SG_VALS,
            'mu' : mu_vals}
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
        return f'{self.source}_{self.target}_{self.binning.label}'
    # -----------------------------------------------
    @classmethod
    def load(
        cls,
        binning : str,
        project : Project,
        source  : Qsq,
        target  : Qsq) -> 'TransferFunctionMakerConf':
        '''
        Parameters
        ---------------
        binning  : Binning, e.g. "block-1 B_PT-2"
        project  : I.e. rk or rkst
        source   : Origin (muon) q2 bin
        target   : Needed (electron) q2 bin

        Returns
        ---------------
        Config object
        '''
        trf_data = gut.load_data(package = 'hqm_data', fpath = 'config/transfer.yaml')
        qsq_data = trf_data['qsq']
        data     = dict()

        for q2_cfg in qsq_data:
            if q2_cfg['source'] != source:
                continue

            if q2_cfg['target'] != target:
                continue

            data.update(q2_cfg)

        binning_conf = BinningConf.load()

        data['fits'      ] = trf_data['fits'       ]
        data['observable'] = trf_data['observable' ]
        data['fft_npt'   ] = trf_data['fft_npt'    ]
        data['bandwidth' ] = trf_data['bandwidth'  ]
        data['components'] = trf_data['models'][project][source]
        data['binning'   ] = binning_conf.from_str(binning = binning)
        data['plots'     ].update(trf_data['plots'])

        return cls(**data)
    # -----------------------------------------------
    @staticmethod
    def print_config(name : str) -> None:
        if not hasattr(TransferFunctionMakerConf, name):
            raise ValueError(f'Cannot find {name} in configuration')

        d_data = getattr(TransferFunctionMakerConf, name)
        log.info(80 * '-')
        log.info(f'{"Setting":<30}{"Value":<50}')
        log.info(80 * '-')
        for key, val in d_data.items():
            log.info(f'{key:<30}{val:<50}')
# -------------------------------------------------------------------
class CCbarRatioCalculatorConf(PDFConf, frozen = True):
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
    def load(cls, binning : str) -> 'CCbarRatioCalculatorConf':
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

        binning_conf           = BinningConf.load()
        rtc_data['observable'] = trf_data['observable']
        rtc_data['binning'   ] = binning_conf.from_str(binning = binning)

        return cls(**rtc_data)
#-------------------------------------------------------------------
