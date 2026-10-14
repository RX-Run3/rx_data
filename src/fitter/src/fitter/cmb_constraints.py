'''
Module with CmbConstraints class
'''

from typing       import Final
from pathlib      import Path
from dmu          import LogStore
from dmu.stats    import ConstraintType, FitParameter, FitResult, zfit
from dmu.workflow import Cache
from dmu.stats    import ConstraintND
from rx_common    import Brem, Trigger, Component, Region
from rx_selection import selection           as sel

from .configs            import CombinatorialConf, RXFitConfig 
from .base_fitter        import BaseFitter
from .likelihood_factory import LikelihoodFactory

log=LogStore.add_logger('fitter:cmb_constraints')
_CONST_TYPE  : Final[ConstraintType] = ConstraintType.gauss # Will use fit results to build these constraints
_DATA_SAMPLE : Final[Component]      = Component.data_24    # What will be used to constrain combinatorial shape
_COMPONENT   : Final[Component]      = Component.comb       # What will be constrained
_SIG_PREFIX  : Final[str]            = 'BREM'               # Signal category prefix
_ERR_METHOD  : Final[str]            = 'minuit_hesse'       # Method used to extract errors
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
        signal  : Signal component, needed to get constraints for CR fit
        cfg_fit : Full fit configuration
        '''
        BaseFitter.__init__(self)

        self._cfg_fit   = cfg_fit
        self._q2bin     = self._cfg_fit.q2bin

        cfg_cmb         = cfg_fit.mod_cfg.components[self._q2bin][_COMPONENT]
        if not isinstance(cfg_cmb, CombinatorialConf):
            ctype = type(cfg_cmb)
            raise ValueError(f'Config for {_COMPONENT} is of type {ctype}')

        self._cfg_cmb   = cfg_cmb
        self._signal    = signal 
        self._mod_cfg   = self._cfg_cmb.constraints.mod_cfg.cfg_clone(
            prefix  = _SIG_PREFIX, 
            q2bin   = self._q2bin,
            brems   = [brem])

        self._brem      = brem
        self._component = _COMPONENT
        self._trigger   = Trigger(self._mod_cfg.trigger)
        self._obs       = self._mod_cfg.obs

        Cache.__init__(
            self,
            out_path = Path(_COMPONENT) / 'fit' / str(self._brem),
            cfg      = cfg_cmb.model_dump())
    # ----------------------
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
    def __fit_cr(self) -> FitResult:
        '''
        Fits the control region

        Returns
        --------------
        Fit result object
        '''
        ftr = LikelihoodFactory(
            name     = str(self._brem),
            obs      = self._obs,
            q2bin    = self._q2bin,
            sample   = _DATA_SAMPLE,
            ph_sample= _COMPONENT,
            cfg      = self._mod_cfg)
        cfg_nll = ftr.run()

        minimizer = zfit.minimize.Minuit()
        zres      = minimizer.minimize(cfg_nll.nll)
        zres.hesse(method = _ERR_METHOD, name = _ERR_METHOD)
        res       = FitResult.from_zfit(res = zres)

        region = Region(brem = self._brem, trigger = self._trigger)

        self._save_fit(
            data    = cfg_nll.nll.data[0],   # Likelihood factory makes NLL for one single region
            model   = cfg_nll.nll.model[0],  # Pick the data and model for that region
            cut_cfg = cfg_nll.selection,
            res     = res, 
            out_path= self._out_path,
            plt_cfg = self._mod_cfg.plots[self._q2bin].regions[region],
        )

        return res
    # ----------------------
    def get_constraint(self) -> ConstraintND:
        '''
        Returns
        ----------------------
        N dimensional Gaussian constraint
        '''
        constraints_path = self._out_path / 'constraints.json'
        if constraints_path.exists():
            log.info(f'Loading combinatorial constraints from: {constraints_path}')
            return ConstraintND.from_json(constraints_path)

        log.info('Constraints not found, calculating them')
        with sel.update_selection(d_sel = self._mod_cfg.selection[self._q2bin]):
            res = self.__fit_cr()

        params : list[FitParameter] = [ param for param in res.parameters if self.__pick_parameter(name = param.name) ]

        values = [ par.value for par in params ]
        names  = [ par.name  for par in params ]

        pars   = self._cfg_cmb.constraints.parameters[self._q2bin]
        cov    = res.pars_covariance(pars = pars)

        cns = ConstraintND(
            name       = str(self._brem),
            kind       = _CONST_TYPE,
            parameters = names, 
            values     = values, 
            cov        = cov,
        )

        cns.to_json(constraints_path)
        self._cache()

        return cns
# ------------------------------------
