'''
Module containing classes meant to be used to validate combinatorial shape
'''
import numpy

from functools   import cached_property
from typing      import Final
from pydantic    import BaseModel
from dmu         import LogStore
from dmu.stats   import FitConf, FitResult, Fitter, ModelFactory, ModelFactoryConf
from dmu.stats   import Model
from dmu.stats   import zfit
from dmu.generic import utilities as gut
from rx_common   import Mass
from rx_common   import Cuts, Qsq, Component, Trigger
from rx_data import RDFGetter

log=LogStore.add_logger('fitter:cmb_validator')

PDF_PREFIX : Final[str] = 'cmb'
# --------------------------------
class CmbFitConf(BaseModel):
    '''
    Fitting configuration
    '''
    conf : FitConf 
    model: ModelFactoryConf
# --------------------------------
class CmbInputConfig(BaseModel):
    '''
    Class meant to configure input for validation
    of configuration
    '''
    q2bin  : Qsq 
    mass   : Mass 
    model  : Model 
    trigger: Trigger 
    sample : Component 
    cutflow: str 
# --------------------------------
class CmbValidationConfig(BaseModel):
    '''
    Class meant to configure selection and fits
    '''
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
    input      : CmbInputConfig
    validation : CmbValidationConfig
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
class CmbValidator:
    '''
    Class meant to validate combinatorial model
    '''
    # ---------------------------
    def __init__(self, cfg : CmbValidatorConf):
        '''
        Parameters
        ----------------
        cfg: Configuration needed for fits, etc
        '''
        self._cfg = cfg

        gtr = RDFGetter(
            trigger= self._cfg.input.trigger,
            sample = self._cfg.input.sample)

        self._rdf = gtr.get_rdf(per_file = False)
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
        rdf  = self._rdf.Filter('mva', cut)
        mass = self._cfg.input.mass

        return rdf.AsNumpy([mass])[mass]
    # ---------------------------
    def run(self) -> ValidationStatus:
        '''
        Runs validation
        '''
        results : dict[str, FitResult] = {}
        for label, cut in self._cfg.cuts.items():
            data  = self._get_data(cut = cut)
            obj   = Fitter(pdf = self.model, data = data)
            results[label] = obj.fit(cfg = self._cfg.validation.fit.conf)

        stat = ValidationStatus(
            input      = self._cfg.input, 
            validation = self._cfg.validation, 
            results    = results)

        return stat
# ---------------------------
