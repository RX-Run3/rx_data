'''
Module containing classes meant to be used to validate combinatorial shape
'''
import numpy
import pandas            as pnd
import matplotlib.pyplot as plt

from pathlib     import Path
from ROOT        import RDF # type: ignore
from functools   import cached_property
from typing      import Final
from pydantic    import BaseModel, ConfigDict
from dmu         import LogStore
from dmu.stats   import ModelFactory, ModelFactoryConf, ZFitPlotter, ZFitPlotterConf
from dmu.stats   import FitConf, FitResult, Fitter
from dmu.stats   import Model
from dmu.stats   import zfit
from dmu.generic import utilities as gut
from rx_common   import Mass
from rx_common   import Cuts, Qsq, Component, Trigger

log=LogStore.add_logger('fitter:cmb_validator')

PDF_PREFIX : Final[str] = 'cmb'
# --------------------------------
class CmbFitConf(BaseModel):
    '''
    Fitting configuration
    '''
    model_config = ConfigDict(frozen=True)

    conf : FitConf 
    model: ModelFactoryConf
# --------------------------------
class CmbInputConfig(BaseModel):
    '''
    Class meant to configure input for validation
    of configuration
    '''
    model_config = ConfigDict(frozen=True)

    q2bin  : Qsq 
    mass   : Mass 
    model  : Model 
    trigger: Trigger 
    sample : Component 
    cutflow: str 
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
    fit       : CmbFitConf
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
    def __hash__(self) -> int:
        return hash(self.model_dump_json())
    # ------------------------
    @property
    def out_dir(self) -> Path:
        '''
        Path to directory where output should go
        '''
        model    = '-'.join(self.validation.fit.model.pdfs)
        cutflow  = self.input.cutflow

        return self.output.dir_path / f'{model}/{cutflow}'
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
            df        = result.df
            df['Fit'] = label
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
        rdf : RDF.RNode,
        cfg : CmbValidatorConf):
        '''
        Parameters
        ----------------
        rdf: DataFrame with data to be fitted
        cfg: Configuration needed for fits, etc
        '''
        self._cfg = cfg
        self._rdf = rdf 
    # ---------------------------
    @cached_property
    def model(self) -> zfit.pdf.BasePDF:
        '''
        Fitting model needed to fit combinatorial proxy
        '''
        cfg = self._cfg.validation.fit.model
        obj = ModelFactory.from_conf(
            obs    = self._cfg.input.mass.obs,
            prefix = PDF_PREFIX,
            cfg    = cfg)

        return obj.get_pdf()
    # ---------------------------
    def _get_data(self, cut : str) -> numpy.ndarray:
        '''
        Array of masses needed for fit
        '''
        rdf  = self._rdf.Filter(cut)
        mass = self._cfg.input.mass

        return rdf.AsNumpy([mass])[mass]
    # ---------------------------
    def _fit(
        self, 
        label: str,
        name : str,
        data : numpy.ndarray) -> FitResult | None:
        '''
        Parameters
        -------------
        label: Identifier for validation run
        name : Used for naming plots
        data : Array with data to fit
        '''
        obj = Fitter(
            pdf  = self.model, 
            data = data)

        try:
            res = obj.fit(cfg = self._cfg.validation.fit.conf)
        except Exception:
            log.warning(f'Fit failed: {label}/{name}')
            return None

        ptr = ZFitPlotter(
            model  = self.model,
            data   = data)
        ptr.run(cfg = self._cfg.output.plots)

        out_dir = self._cfg.out_dir / label
        out_dir.mkdir(parents = True, exist_ok = True)

        plt.savefig(out_dir / f'{name}.png')
        plt.close('all')

        return res
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
            data  = self._get_data(cut = cut)

            nentries = len(data)
            if nentries == 0:
                log.warning(f'No entries found for: {cut}')
                continue

            log.debug(f'Found {nentries} for: {cut}')
            res = self._fit(
                label= label,
                name = cut_name,
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
