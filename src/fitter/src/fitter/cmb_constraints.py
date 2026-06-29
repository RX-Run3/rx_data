'''
Module with CmbConstraints class
'''

from typing       import Final, Sequence
from pathlib      import Path
from dmu          import LogStore
from dmu.stats    import ConstraintType, FitParameter, zfit, FitResult
from dmu.stats    import Constraint, ConstraintAdder
from dmu.workflow import Cache
from dmu.stats    import ConstraintND
from zfit.pdf     import BasePDF             as zpdf
from rx_common    import Brem, Trigger, Component
from rx_selection import selection           as sel

from .prec_scales        import get_constraints as get_prec_constraints
from .configs            import CombinatorialConf, RXFitConfig 
from .base_fitter        import BaseFitter
from .data_fitter        import DataFitter
from .signal_constraints import SignalConstraints
from .likelihood_factory import LikelihoodFactory, NLLConf

log=LogStore.add_logger('fitter:cmb_constraints')
_DATA_SAMPLE : Final[Component] = Component.data_24 # What will be used to constrain combinatorial shape
_COMPONENT   : Final[Component] = Component.comb    # What will be constrained
_SIG_PREFIX  : Final[str]       = 'BREM'            # Signal category prefix
# ------------------------------------
class CmbConstraints(BaseFitter, Cache):
    '''
    Class intended to provide constraints for shape of combinatorial model
    '''
    # ----------------------
    def __init__(
        self, 
        brem    : Brem,
        signal  : Component,
        cfg_fit : RXFitConfig) -> None:
        '''
        Parameters
        -------------
        brem    : Brem category to fit 
        nll     : Likelihood that needs constraining
        signal  : Signal component, needed to get constraints for CR fit
        cfg_cmb : fit configuration for combinatorial component
        cfg_fit : Full fit configuration
        q2bin   : E.g. central
        '''
        BaseFitter.__init__(self)

        self._cfg_fit   = cfg_fit
        cfg_cmb         = cfg_fit.mod_cfg.components[_COMPONENT]
        if not isinstance(cfg_cmb, CombinatorialConf):
            ctype = type(cfg_cmb)
            raise ValueError(f'Config for {_COMPONENT} is of type {ctype}')

        self._cfg_cmb   = cfg_cmb
        self._mod_cfg   = self._cfg_cmb.constraints.mod_cfg.cfg_clone(prefix = _SIG_PREFIX, regions = [brem.region])
        self._signal    = signal 

        self._brem      = brem
        self._reg       = brem.region 
        self._q2bin     = self._cfg_fit.q2bin
        self._component = _COMPONENT
        self._base_path = Path(Component.comb) / 'fit' / self._reg
        self._trigger   = Trigger(self._mod_cfg.trigger)
        self._obs       = self._mod_cfg.obs

        Cache.__init__(
            self,
            out_path = self._base_path,
            cfg      = cfg_cmb.model_dump())
    # ----------------------
    def _get_basic_models(self, models : list[zpdf]) -> list[zpdf]:
        '''
        Parameters
        -------------
        models: List of PDFs

        Returns
        -------------
        List of PDFs where the SumPDF ones have been unpacked
        '''
        basic_models : list[zpdf] = []
        for pdf in models:
            if not isinstance(pdf, zfit.pdf.SumPDF):
                basic_models.append(pdf)
                continue

            basic_models += self._get_basic_models(models = pdf.pdfs)

        return basic_models
    # ----------------------
    def _model_from_models(self, models : list[zpdf]) -> zpdf:
        '''
        Parameters
        -------------
        models: List of PDFs 

        Returns
        -------------
        Combinatorial PDF if found one and only one model, 
        otherwise it will raise ValueError
        '''
        cmb_models : list[zpdf] = []

        for pdf in models: 
            if Component.comb not in pdf.name:
                log.debug(f'Skipping non-combinatorial: {pdf.name}')
                continue

            log.debug(f'Found combinatorial: {pdf.name}')
            if self._reg      not in pdf.name:
                continue

            log.info(f'Picking: {pdf.name}')
            cmb_models.append(pdf)

        if len(cmb_models) == 1:
            return cmb_models[0]

        log.error(20 * '-')
        log.error('Existing:')
        for pdf in models:
            log.error(pdf.name)

        log.error(20 * '-')
        log.error('Found:')
        for pdf in cmb_models:
            log.error(pdf.name)

        raise ValueError('Not found one and only one combinatorial model')
    # ---------------------
    def __pick_parameter(self, name : str) -> bool:
        '''
        Parameters
        -------------
        name: Parameter name from SS fit

        Returns
        -------------
        True if this parameter is meant to be constrained
        '''
        par_names = self._cfg_cmb.constraints.parameters[self._q2bin]

        return any( name.startswith(par_name) for par_name in par_names )
    # ----------------------
    def _add_constraints(
        self,
        cons   : Sequence[Constraint],
        cfg_nll: NLLConf) -> NLLConf:
        '''
        Parameters
        -------------
        cons    : List of constraints
        cfg_nll : Likelihood wrapper
    
        Returns
        -------------
        Wrapper with constrained NLL
        '''
        if not cons:
            log.warning('Not using any constraints')
    
        log.info('Constraints:')
        for constraint in cons:
            log.info(constraint)
    
        cad  = ConstraintAdder(
            nll=cfg_nll.nll, 
            constraints=cons)
        nll  = cad.get_nll()

        return NLLConf(
            nll         = nll,
            constraints = cons,
            selection   = cfg_nll.selection,
        )
    # ---------------------
    def _fit_cr(self) -> FitResult:
        '''
        Fits the control region

        Returns
        --------------
        Fit result object
        '''
        ftr        = LikelihoodFactory(
            name   = self._reg,
            obs    = self._obs,
            q2bin  = self._q2bin,
            sample = _DATA_SAMPLE,
            cfg    = self._mod_cfg)
        cfg_nll    = ftr.run()

        constraints= get_prec_constraints(
            brem   = self._brem,
            pars   = [ par.name for par in cfg_nll.nll.get_params() ],
            signal = self._signal,
            cfg    = self._cfg_fit, 
        )

        calc       = SignalConstraints(
            comp   = self._signal,
            nll    = cfg_nll.nll,
        )
        constraints += calc.get_constraints()

        cfg_nll     = self._add_constraints(
            cons    = constraints,
            cfg_nll = cfg_nll)

        ftr       = DataFitter(
            q2bin = self._q2bin,
            d_nll = { self._reg: cfg_nll },
            cfg   = self._mod_cfg)
        res = ftr.run()

        self._save_fit(
            data    = cfg_nll.nll.data[0],   # Likelihood factory makes NLL for one single region
            model   = cfg_nll.nll.model[0],  # Pick the data and model for that region
            cut_cfg = cfg_nll.selection,
            res     = res, 
            out_path= self._out_path,
            plt_cfg = self._mod_cfg.plots.regions[self._reg],
        )

        return res
    # ----------------------
    def get_constraint(self) -> ConstraintND:
        '''
        Returns
        ----------------------
        N dimensional Gaussian constraint
        '''
        log.info('Constraints not found, calculating them')

        with sel.update_selection(d_sel = self._mod_cfg.selection[self._q2bin]):
            res = self._fit_cr()

        params : list[FitParameter] = [ param for param in res.parameters if self.__pick_parameter(name = param.name) ]

        values = [ par.value for par in params ]
        names  = [ par.name  for par in params ]

        pars   = self._cfg_cmb.constraints.parameters[self._q2bin]
        cov    = res.pars_covariance(pars = pars)

        cns = ConstraintND(
            name       = self._reg, 
            kind       = ConstraintType.gauss,
            parameters = names, 
            values     = values, 
            cov        = cov,
        )

        constraints_path = self._out_path / 'constraints.json'
        cns.to_json(constraints_path)

        return cns
# ------------------------------------
