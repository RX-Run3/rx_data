'''
Module containing DataModel class
'''

from typing         import Final
from contextlib     import contextmanager
from dmu            import LogLevels, LogStore
from dmu.stats      import print_pdf, zfit
from dmu.stats      import ParameterLibrary as PL
from rx_common      import Component, Qsq, Trigger
from rx_data        import SpecMaker
from zfit           import Space         as zobs
from zfit.pdf       import BasePDF       as zpdf
from zfit.exception import ParamNameNotUniqueError

from .configs       import FitModelConf
from .sim_fitter    import SimFitter

log = LogStore.add_logger('fitter:data_model')

_MAIN_CATEGORY_NAME : Final[str] = 'main'
# ------------------------
class DataModel:
    '''
    Model for fitting data samples
    '''
    _skipped_components : list[str] = []
    # ------------------------
    def __init__(
        self,
        cfg     : FitModelConf,
        obs     : zobs,
        trigger : Trigger,
        q2bin   : Qsq,
        name    : str):
        '''
        Parameters
        ------------------
        cfg    : Configuration object
        trigger: Hlt2RD...
        project: E.g. rx
        q2bin  : E.g. central
        obs    : zfit observable
        name   : Optional, identifier for this model, 
                 if passed, used also as suffix of yields, e.g. yld_combinatorial_{name}
        '''
        self._cfg    = cfg
        self._obs    = obs
        self._trigger= trigger
        self._q2bin  = q2bin
        self._name   = name
    # ------------------------
    def _extend(
        self, 
        pdf       : zpdf, 
        component : Component) -> zpdf:
        '''
        Parameters
        -------------------
        component: Fit component
        pdf      : zfit pdf

        Returns
        -------------------
        PDF with yield
        '''
        yield_name = f'yld_{component}' if self._name == _MAIN_CATEGORY_NAME else f'yld_{component}_{self._name}'
        pdf_name   = f'{component}_{self._name}'

        nevt = PL.get_yield(name=yield_name)
        kdes = zfit.pdf.KDE1DimFFT, zfit.pdf.KDE1DimExact, zfit.pdf.KDE1DimISJ
        if isinstance(pdf, kdes):
            pdf.set_yield(nevt)
            return pdf

        log.info(f'Extending {component} with {yield_name}')
        pdf = pdf.create_extended(nevt, name=pdf_name)

        return pdf
    # ------------------------
    def get_model(self) -> zpdf:
        '''
        Returns 
        ----------------
        Fitting model for data fit
        '''
        l_pdf = []
        npdf  = len(self._cfg.components)
        if npdf == 0:
            raise ValueError('Found zero components in model')

        log.debug(f'Found {npdf} components')

        for component, cfg in self._cfg.components.items():
            # If component has its own trigger (e.g. MisID with its noPID) pick that
            # otherwise pick full model trigger
            trigger = self._cfg.trigger if cfg.component_trigger is None else cfg.component_trigger 

            if component in self._skipped_components:
                log.warning(f'Skipping {component} component')
                continue

            log.info(f'Building: {component}')
            with SpecMaker.project(name = trigger.project):
                ftr  = SimFitter(
                    name     = self._name,
                    component= component,
                    trigger  = trigger,
                    q2bin    = self._q2bin,
                    cfg      = cfg,
                    obs      = self._obs)
                pdf = ftr.get_model()

            if pdf is None:
                log.warning(f'Cannot build component: {component}')
                continue

            pdf = self._extend(pdf=pdf, component=component)
            l_pdf.append(pdf)

        if len(l_pdf) == 1:
            log.warning('Found only one PDF, not using it in SumPDF')
            return l_pdf[0]

        try:
            pdf = zfit.pdf.SumPDF(obs = self._obs, pdfs = l_pdf)
        except ParamNameNotUniqueError as exc:
            for pdf in l_pdf:
                log.error('-----------------')
                print_pdf(pdf = pdf, level = LogLevels.error)
            raise ValueError('Cannot add PDFs') from exc

        return pdf
    # ------------------------
    @classmethod
    def skip_components(cls, names : list[str]):
        '''
        Parameters
        ------------
        names: Names of components to be skipped, from data.yaml
        '''
        log.warning(f'Excluding components: {names}')

        @contextmanager
        def _context():
            old_val = cls._skipped_components
            cls._skipped_components = names

            try:
                yield
            finally:
                cls._skipped_components = old_val

        return _context()
# ------------------------
