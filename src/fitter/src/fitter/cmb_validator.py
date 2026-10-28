'''
Module containing classes meant to be used to validate combinatorial shape
'''
import numpy
import pandas            as pnd
import matplotlib.pyplot as plt

from pathlib     import Path
from ROOT        import RDF
from typing      import Final
from pydantic    import BaseModel, ConfigDict, model_validator
from dmu         import LogStore
from dmu.stats   import ModelFactory, ModelFactoryConf, ZFitPlotter, ZFitPlotterConf
from dmu.stats   import FitConf, FitResult, Fitter
from dmu.stats   import zfit
from dmu.generic import utilities as gut
from rx_common   import Mass
from rx_common   import Cuts, Qsq, Component, Trigger
from zfit.pdf    import BasePDF

log=LogStore.add_logger('fitter:cmb_validator')

_PDF_PREFIX    : Final[str] = 'cmb'
_MIN_DATA_SIZE : Final[int] = 50
# --------------------------------
class CmbFitConf(BaseModel):
    '''
    Fitting configuration
    '''
    model_config = ConfigDict(frozen=True)

    conf : FitConf 
    model: ModelFactoryConf | None
# --------------------------------
class CmbInputConfig(BaseModel):
    '''
    Class meant to configure input for validation
    of configuration
    '''
    model_config = ConfigDict(frozen=True)

    q2bin  : Qsq 
    mass   : Mass 
    trigger: Trigger 
    samples: list[Component]
    cutflow: str 
    # -------------------------------------
    @model_validator(mode = 'after')
    def validate_samples(self) -> 'CmbInputConfig':
        unique_samples = set(self.samples)

        assert len(unique_samples) == len(self.samples)

        return self
# --------------------------------
class CmbOutputConfig(BaseModel):
    '''
    Class meant to store configurations
    to save results, e.g. plots
    '''
    model_config = ConfigDict(frozen=True)

    plots    : ZFitPlotterConf
    dir_path : Path
    # --------------------
    def out_dir(self, extend : str | None = None) -> Path:
        '''
        Parameters
        -----------------
        extend: Ending of path to be appended to dir_path, e.g. test/expo/

        Returns
        -----------------
        Path to directory, directory has already been made
        '''
        if extend is None:
            self.dir_path.mkdir(parents = True, exist_ok = True)
            return self.dir_path

        dir_path = self.dir_path / extend
        dir_path.mkdir(parents = True, exist_ok = True)

        return dir_path
# --------------------------------
class CmbValidationConfig(BaseModel):
    '''
    Class meant to configure selection and fits
    '''
    model_config = ConfigDict(frozen=True)

    selection : dict[Cuts,str]
    cutflows  : dict[str,dict[str,str]]
    fit       : dict[Component,CmbFitConf]
    # ---------------------------
    @classmethod
    def from_file(cls, fname : str) -> 'CmbValidationConfig':
        '''
        Parameters
        ---------------
        fname: Yaml file name where configuration is specified 

        Returns
        ---------------
        Config object
        '''
        data = gut.load_data(
            package = 'fitter_data',
            fpath   = fname)

        return cls(**data)
# --------------------------------
class CmbValidatorConf(BaseModel):
    '''
    Class meant to configure validation
    '''
    model_config = ConfigDict(frozen=True)

    input      : CmbInputConfig
    validation : CmbValidationConfig
    output     : CmbOutputConfig
    # ------------------------
    @model_validator(mode = 'after')
    def validate_samples(self) -> 'CmbValidatorConf':
        '''
        Check that every sample requested
        has a config section in the yaml file
        '''
        in_samples = set(self.input.samples)
        ot_samples = set(self.validation.fit)

        fail = False
        for needed_sample in in_samples:
            if needed_sample in ot_samples:
                continue

            log.error(f'Missing {needed_sample} in config file')
            fail = True

        if fail:
            raise ValueError('At least one sample missing in config')

        return self
    # ------------------------
    def __hash__(self) -> int:
        return hash(self.model_dump_json())
    # ------------------------
    def out_dir(self, component : Component) -> Path:
        '''
        Path to directory where output should go
        '''
        cfg_fit  = self.validation.fit[component]
        model    = cfg_fit.model
        pdfs     = model.pdfs if model else ['kde']

        model    = '-'.join(pdfs)
        cutflow  = self.input.cutflow
        q2bin    = self.input.q2bin
        trigger  = self.input.trigger

        return self.output.dir_path / f'{trigger.value}/{q2bin}/{cutflow}/{component}/{model}'
    # ------------------------
    @property
    def cuts(self) -> dict[str,str]:
        '''
        Dictionary mapping label of cut and value
        Needed to scan MVA plane
        '''
        return self.validation.cutflows[self.input.cutflow]
# ----------------------
class ValidationStatus(BaseModel):
    '''
    Class meant to represent status of fits
    used for validation
    '''
    input      : CmbInputConfig
    validation : CmbValidationConfig
    results    : dict[str,FitResult]
    # ----------------------
    @property
    def df(self) -> pnd.DataFrame:
        '''
        DataFrame with all the parameters form all the fits
        '''
        l_df : list[pnd.DataFrame] = []
        for label, result in self.results.items():
            gof = result.gof
            if gof is None:
                raise ValueError(f'GOF not found: {result}')

            df              = result.df
            df.loc[len(df)] = ['pvalue', gof.pval, 0.1]
            df['Fit']       = label
            l_df.append(df)

        df = pnd.concat(l_df)
        df = df.reset_index(drop = True)

        return df
# ----------------------
class CmbValidator:
    '''
    Class meant to validate combinatorial model
    '''
    # ---------------------------
    def __init__(
        self, 
        rdfs    : dict[Component, RDF.RNode],
        cfg     : CmbValidatorConf):
        '''
        Parameters
        ----------------
        rdfs : Dictionary mapping component with dataframe holding data
        cfg  : Configuration needed for fits, etc
        '''
        self._cfg  = cfg
        self._rdfs = rdfs
    # ---------------------------
    def _get_model(
        self, 
        cut  : str,
        label: str,
        name : str) -> zfit.pdf.BasePDF:
        '''
        Parameters
        ----------------
        cut : BDT cut for current model 
        name: Identifier of current model

        Returns
        ----------------
        PDF used for fit to data
        '''
        l_pdf : list[BasePDF] = []
        for component in self._cfg.input.samples:
            log.info(f'Getting PDF for: {component}')

            cfg_fit = self._cfg.validation.fit[component]
            pdf     = self._pdf_for_component(
                cut       = cut,
                name      = name,
                label     = label,
                component = component, 
                cfg       = cfg_fit)

            if pdf is None:
                continue

            par_name = f'nev_{component}' if component.is_mc else 'nev'
            nev      = zfit.Parameter(par_name, 10, 0, 1000_000)
            pdf.set_yield(nev)

            l_pdf.append(pdf)

        if len(l_pdf) == 1:
            return l_pdf[0]

        return zfit.pdf.SumPDF(l_pdf, obs = self._cfg.input.mass.obs) 
    # ----------------------
    def _pdf_for_component(
        self, 
        cut       : str,
        name      : str,
        label     : str,
        component : Component, 
        cfg       : CmbFitConf) -> zfit.pdf.BasePDF | None:
        '''
        Parameters
        -------------
        component: Component to fit, e.g. data
        cfg      : Configuration for fit

        Returns
        -------------
        PDF needed to model component or None if fewer than
        _MIN_DATA_SIZE entries found
        '''
        log.info(f'Building parametric PDF for {component}')
        mass = self._cfg.input.mass

        pdf = None
        if cfg.model:
            obj  = ModelFactory.from_conf(
                obs    = mass.obs, 
                prefix = _PDF_PREFIX,
                cfg    = cfg.model)
            pdf = obj.get_pdf()

        if not pdf and not component.is_mc:
            raise ValueError(f'Missing model for {component}')
        elif           not component.is_mc:
            log.debug(f'Component {component} is not MC, not fitting')
            return pdf

        log.debug(f'Applying selection {cut} for {component}')
        rdf              = self._rdfs[component].Filter(cut)
        masses           = rdf.AsNumpy([mass])[mass]
        lower, upper     = self._cfg.input.mass.limits
        masses_in_bounds = masses[(masses > lower) & (masses < upper)]

        if len(masses_in_bounds) < _MIN_DATA_SIZE:
            log.warning(f'Found {len(masses_in_bounds)} entries for {component} at {name}, skipping')
            return None

        if not pdf:
            log.info(f'Using KDE for: {component}')
            obs   = zfit.Space('mass', limits = (4000, 6000))
            model = zfit.pdf.KDE1DimFFT(
                name = component.latex,
                data = masses, 
                obs  = obs,
                norm = mass.obs)

            self._plot_fit(
                data  = masses,
                model = model,
                label = label,
                name  = name ,
                comp  = component )

            return model
        else:
            log.info(f'Using {cfg.model} for {component}')

        log.info(f'Found {len(masses)} entries for {component} at {name}')
        self._fit(
            comp  = component,
            model = pdf,
            data  = masses,
            name  = name,
            label = label)

        if not cfg.model:
            return pdf

        log.debug('Fixing parameters:')
        for par in pdf.get_params():
            log.debug(f'   {par.name}')
            par.floating = False

        return pdf
    # ---------------------------
    def _get_data(self, cut : str) -> numpy.ndarray:
        '''
        Parameters
        --------------
        cut: BDT cut

        Returns
        -------------
        Array of masses needed for fit
        '''
        rdf  = self._rdfs[Component.data_24].Filter(cut, 'BDT')
        mass = self._cfg.input.mass

        data = rdf.AsNumpy([mass])[mass]

        nentries = len(data)
        if nentries == 0:
            rep = rdf.Report()
            rep.Print()

            raise ValueError(f'No entries found for: {cut}')

        log.debug(f'Found {nentries} for: {cut}')

        return data
    # ---------------------------
    def _fit(
        self, 
        label: str,
        name : str,
        comp : Component,
        model: zfit.pdf.BasePDF,
        data : numpy.ndarray) -> FitResult | None:
        '''
        Parameters
        -------------
        label: Identifier for validation run
        name : Used for naming plots
        comp : Component that will be fitted
        model: PDF to fit
        data : Array with data to fit
        '''
        log.debug(f'Fitting MC component: {comp}')
        obj = Fitter(
            pdf  = model, 
            data = data)

        cfg = self._cfg.validation.fit[comp]
        try:
            res = obj.fit(cfg = cfg.conf)
        except Exception:
            log.warning(f'Fit failed: {label}/{name}')
            return None

        self._plot_fit(
            data  = data ,
            model = model,
            label = label,
            name  = name ,
            comp  = comp )

        return res
    # ----------------------
    def _plot_fit(
        self,
        data : numpy.ndarray,
        model: zfit.pdf.BasePDF,
        label: str,
        name : str,
        comp : Component) -> None:
        '''
        Parameters
        -------------
        label: Identifier for validation run
        name : Used for naming plots
        comp : Component that will be fitted
        model: PDF to fit
        data : Array with data to fit
        '''
        log.debug('Plotting fit')

        lower, upper   = self._cfg.input.mass.limits
        data_in_bounds = data[(data > lower) & (data < upper)]

        title      = f'{name}; Entries = {len(data_in_bounds)}'
        cfg_plt    = self._cfg.output.plots.model_copy(update = {'title' : title})

        ptr        = ZFitPlotter(
            model  = model,
            data   = data)
        ptr.run(cfg = cfg_plt)

        out_dir = self._cfg.out_dir(component = comp) / label

        out_dir.mkdir(parents = True, exist_ok = True)

        out_path = out_dir / f'{name}.png'
        log.debug(f'Saving plot to: {out_path}')
        plt.savefig(out_path)
        plt.close('all')
    # ---------------------------
    def run(
        self,
        label : str) -> ValidationStatus:
        '''
        Parameters
        --------------
        label: Identifier of this validation
        '''
        results : dict[str, FitResult] = {}
        for cut_name, cut in self._cfg.cuts.items():
            data = self._get_data(cut = cut)
            model= self._get_model(
                cut  = cut,
                label= label,
                name = cut_name)

            res = self._fit(
                label= label,
                name = cut_name,
                comp = Component.data_24,
                model= model,
                data = data)

            if res is None:
                continue

            results[cut_name] = res

        stat = ValidationStatus(
            input      = self._cfg.input, 
            validation = self._cfg.validation, 
            results    = results)

        return stat
# ---------------------------
