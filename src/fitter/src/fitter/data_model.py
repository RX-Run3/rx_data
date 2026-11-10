'''
Module containing DataModel class
'''

from typing         import Final
from contextlib     import contextmanager
from dmu            import LogLevels, LogStore
from dmu.stats      import print_pdf, zfit
from dmu.stats      import ParameterLibrary as PL
from rx_common      import Component, Project, Qsq, Trigger
from rx_data        import SpecMaker
from zfit           import Space         as zobs
from zfit.pdf       import BasePDF       as zpdf

from .configs       import AnyModelConf, FitModelConf, CCbarConfTF
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
                 if passed, used also as suffix of yields, e.g. yld_comb_rk_{name}
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
        yield_name = f'yld_{component}_{self._trigger.project}'
        yield_name = yield_name if self._name == _MAIN_CATEGORY_NAME else f'{yield_name}_{self._name}'
        pdf_name   = f'{component}_{self._name}'

        nevt = PL.get_yield(name=yield_name)
        kdes = zfit.pdf.KDE1DimFFT, zfit.pdf.KDE1DimExact, zfit.pdf.KDE1DimISJ
        if isinstance(pdf, kdes):
            pdf.set_yield(nevt)
            return pdf

        log.info(f'Extending {component} with {yield_name}')
        pdf = pdf.create_extended(nevt, name=pdf_name)

        return pdf
    # ----------------------
    def _get_component_project_trigger(self, cfg : AnyModelConf) -> tuple[Project | None, Trigger]:
        '''
        Parameters
        -------------
        cfg : Configuration associated to component

        Returns
        -------------
        Tuple with:

        - Project If different from the one used by Data, otherwise None
        - Trigger needed for component
        '''
        # Component has no trigger specified => Do not override project, use Data trigger
        if cfg.component_trigger is None:
            return None, self._cfg.trigger

        # Component has trigger and is the same as the Data one => Do not override project, use Data trigger
        if self._cfg.trigger == cfg.component_trigger:
            return None, self._cfg.trigger

        # Component has trigger and it different from data => Override project and trigger
        return cfg.component_trigger.project, cfg.component_trigger
    # ------------------------
    def _get_sim_fit_pdf(
        self,
        cfg       : AnyModelConf,
        component : Component) -> zpdf | None:
        '''
        Parameters
        ----------------
        cfg      : Config needed to build model's component
        component: Fit component

        Returns
        ----------------
        zfit PDF representing component or None if component is skipped/not found
        '''
        if component in self._skipped_components:
            log.warning(f'Skipping {component} component')
            return None

        log.info(20 * '-')
        log.info(f'Building component {component} with {cfg.cfg_obs}')
        log.info(20 * '-')
        proj, trig = self._get_component_project_trigger(cfg = cfg)
        with SpecMaker.project(project = proj):
            ftr  = SimFitter(
                name     = self._name,
                component= component,
                trigger  = trig,
                q2bin    = self._q2bin,
                cfg      = cfg)
            pdf = ftr.get_model()

        if pdf is None:
            log.warning(f'Cannot build component: {component}')

        return pdf
    # ------------------------
    def _add_components(self, d_pdf : dict[Component, zpdf]) -> zpdf:
        '''
        Parameters
        ----------------
        d_pdf: Dictionary mapping fitting component to corresponding PDF

        Returns
        ----------------
        Sum of components
        '''
        components = self._cfg.components[self._q2bin]

        l_pdf : list[zpdf] = []
        for component in components:
            if component not in d_pdf:
                continue

            pdf = d_pdf[component]                           # Sort by component
            pdf = self._extend(pdf=pdf, component=component) # Extend
            l_pdf.append(pdf)

        if len(l_pdf) == 1:
            log.warning('Found only one PDF, not using it in SumPDF')
            return l_pdf[0]

        try:
            pdf = zfit.pdf.SumPDF(obs = self._obs, pdfs = l_pdf)
        except Exception as exc:
            for pdf in l_pdf:
                log.error('-----------------')
                print_pdf(pdf = pdf, level = LogLevels.error)
            raise ValueError(f'Cannot add PDFs with obs: {self._obs}') from exc

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
    def get_model(self) -> zpdf:
        '''
        Returns
        ----------------
        Fitting model for data fit
        '''
        components = self._cfg.components[self._q2bin]
        npdf       = len(components)
        if npdf == 0:
            raise ValueError('Found zero components in model')

        log.debug(f'Found {npdf} components')

        d_pdf : dict[Component, zpdf] = dict()
        for component, cfg in components.items():
            if not cfg.from_sim_fit:
                continue

            pdf           = self._get_sim_fit_pdf(
                component = component,
                cfg       = cfg)

            if pdf is None:
                continue

            d_pdf[component] = pdf

        for component, cfg in components.items():
            if cfg.from_sim_fit:
                continue

            if not isinstance(cfg, CCbarConfTF):
                this_type = type(cfg)
                raise ValueError(f'Config is not a ccbar TTF config but {this_type}')

            obs_names = self._obs.obs
            if obs_names is None:
                raise ValueError(f'Cannot find observable name in: {self._obs}')

            d_pdf[component] = cfg.get_pdf(
                obs_name= obs_names[0],
                project = self._trigger.project,
                pdfs    = d_pdf)

        return self._add_components(d_pdf = d_pdf)
# ------------------------
