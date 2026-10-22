'''
Module containing DataFitter class
'''
from dmu                import LogStore
from dmu.stats          import zfit
from dmu.stats          import Constraint
from typing             import Sequence
from rx_common          import Project, Qsq, Component, Cuts
from rx_data            import RDFGetter
from rx_selection       import selection  as sel
from contextlib         import ExitStack
from zfit.loss          import ExtendedUnbinnedNLL
from zfit               import Space  as zobs

from pydantic           import BaseModel, ConfigDict
from .configs           import FitModelConf
from .data_preprocessor import DataPreprocessor
from .data_model        import DataModel

log=LogStore.add_logger('fitter:likelihood_factory')
# ----------------------
class NLLConf(BaseModel, frozen = True):
    '''
    Wrapper to NLL and associated objects
    '''
    model_config = ConfigDict(arbitrary_types_allowed = True)

    nll        : ExtendedUnbinnedNLL
    selection  : dict[str, dict[Cuts,str]]
    constraints: Sequence[Constraint]
# ------------------------
class LikelihoodFactory:
    '''
    Builder of likelihoods for real data (not MC) given a:

    - Data sample
    - Configuration describing the models to use

    Basically a wrapper for DataModel and DataPreprocessor
    '''
    # ------------------------
    def __init__(
        self,
        obs       : zobs,
        sample    : Component,
        q2bin     : Qsq,
        cfg       : FitModelConf,
        name      : str,
        ph_sample : Component | None = None):
        '''
        Parameters
        ------------------
        obs      : zfit observable
        sample   : Identifies data sample e.g. DATA_24_MagUp...
        q2bin    : E.g. central
        cfg      : Configuration for the fit to data
        name     : Identifier for fit, e.g. block. This is optional
        ph_sample: Physical sample. Represents what sample will be used for.
                     E.g. data_24 -> comb, data_24 -> misID, etc. Only makes sense for data
        '''
        self._name      = name
        self._obs       = obs
        self._sample    = sample
        self._trigger   = cfg.trigger
        self._q2bin     = q2bin
        self._cfg       = cfg
        self._ph_sample = ph_sample
    # ----------------------
    def _get_config(self) -> dict[str,dict[Cuts,str]]:
        '''
        Returns
        -------------
        Dictionary storing selection, default and for fit
        '''
        log.debug('Retrieving NLL configuration')

        cuts_fit = sel.selection(
            process=self._sample,
            trigger=self._trigger,
            q2bin  =self._q2bin)

        with sel.custom_selection(d_sel={}, force_override=True):
            cuts_def = sel.selection(
                process=self._sample,
                trigger=self._trigger,
                q2bin  =self._q2bin)

        return {
            'default' : cuts_def,
            'fit'     : cuts_fit}
    # ------------------------
    def run(
        self,
        project : Project | None = None) -> NLLConf:
        '''
        Creates negative log-likelihood

        Returns
        ------------
        Zfit likelihood
        '''
        log.info(30 * '-')
        log.info(f'Getting real data: {self._sample}/{self._trigger}/{self._q2bin}')
        log.info(30 * '-')

        with ExitStack() as stack:
            if project:
                stack.enter_context(RDFGetter.project(project = project))

            dpr  = DataPreprocessor(
                name      = self._name,
                obs       = self._obs,
                q2bin     = self._q2bin,
                sample    = self._sample,
                trigger   = self._trigger,
                ph_sample = self._ph_sample,
                wgt_cfg   = None) # Do not need weights for data
            data = dpr.get_data()

        log.info('Getting full data model using fits to simulation')
        log.debug(f'{"Trigger":<20}{self._trigger}')
        log.debug(f'{"q2bin  ":<20}{self._q2bin}')
        mod  = DataModel(
            name   = self._name,
            cfg    = self._cfg,
            obs    = self._obs,
            q2bin  = self._q2bin,
            trigger= self._trigger)
        model= mod.get_model()

        log.info(50 * '-')
        log.info(f'Making {self._name} likelihood')
        log.info(50 * '-')

        nll = zfit.loss.ExtendedUnbinnedNLL(model=model, data=data)

        cfg = NLLConf(
            selection   = self._get_config(),
            nll         = nll,
            constraints = [])

        return cfg
# ------------------------
