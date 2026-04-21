'''
Module with CmbConstraints class
'''

from typing       import Final
from pathlib      import Path
from dmu          import LogStore
from dmu.stats    import Constraint, ConstraintAdder, ConstraintType, FitParameter, zfit, FitResult
from dmu.workflow import Cache
from dmu.stats    import ConstraintND
from zfit.loss import ExtendedUnbinnedNLL
from zfit.pdf     import BasePDF             as zpdf
from rx_common    import Brem, Trigger, Component

from .configs            import CombinatorialConf, RXFitConfig 
from .base_fitter        import BaseFitter
from .data_fitter        import DataFitter
from .likelihood_factory import LikelihoodFactory, NLLConf

log=LogStore.add_logger('fitter:cmb_constraints')
DATA_SAMPLE : Final[Component] = Component.data_24 # What will be used to constrain
COMPONENT   : Final[Component] = Component.comb    # What will be constrained
SIG_PREFIX  : Final[str]       = 'BREM'            # Signal category prefix
# ------------------------------------
class CmbConstraints(BaseFitter, Cache):
    '''
    Class intended to provide constraints for shape of combinatorial model
    '''
    # ----------------------
    def __init__(
        self, 
        brem    : Brem,
        cfg_cmb : CombinatorialConf,
        cfg_fit : RXFitConfig) -> None:
        '''
        Parameters
        -------------
        brem    : Brem category to fit 
        nll     : Likelihood that needs constraining
        cfg_cmb : fit configuration for combinatorial component
        cfg_fit : Full fit configuration
        q2bin   : E.g. central
        '''
        BaseFitter.__init__(self)

        self._cfg_fit   = cfg_fit
        self._cfg_cmb   = cfg_cmb
        self._mod_cfg   = cfg_cmb.constraints.mod_cfg.cfg_clone(prefix = SIG_PREFIX, regions = [brem.region])

        self._brem      = brem
        self._reg       = brem.region 
        self._q2bin     = self._cfg_fit.q2bin
        self._component = COMPONENT
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
    def _pick_parameter(self, name : str) -> bool:
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
    # ---------------------
    def _fit_cr(self) -> FitResult:
        '''
        Fits the control region

        Returns
        --------------
        Fit result object
        '''
        ftr       = LikelihoodFactory(
            name   = self._reg,
            obs    = self._obs,
            q2bin  = self._q2bin,
            sample = DATA_SAMPLE,
            cfg    = self._mod_cfg)
        cfg_nll   = ftr.run()

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

        res       = self._fit_cr()
        par_names = self._cfg_cmb.constraints.parameters[self._q2bin]
        params : list[FitParameter] = [ param for param in res.parameters if param.name in par_names ]

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
