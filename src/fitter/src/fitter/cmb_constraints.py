'''
Module with CmbConstraints class
'''

from typing       import Final
from pathlib      import Path
from dmu          import LogStore
from dmu.stats    import ConstraintType, FitParameter, FitResult
from dmu.workflow import Cache
from dmu.stats    import ConstraintND
from rx_common    import Brem, Trigger, Component
from rx_selection import selection           as sel

from .configs            import CombinatorialConf, RXFitConfig 
from .base_fitter        import BaseFitter
from .data_fitter        import DataFitter
from .likelihood_factory import LikelihoodFactory

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
            regions = [brem.region])

        self._reg       = brem.region 
        self._component = _COMPONENT
        self._base_path = Path(Component.comb) / 'fit' / self._reg
        self._trigger   = Trigger(self._mod_cfg.trigger)
        self._obs       = self._mod_cfg.obs

        Cache.__init__(
            self,
            out_path = self._base_path,
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
        ftr        = LikelihoodFactory(
            name   = self._reg,
            obs    = self._obs,
            q2bin  = self._q2bin,
            sample = _DATA_SAMPLE,
            cfg    = self._mod_cfg)
        cfg_nll    = ftr.run()

        ftr       = DataFitter(
            q2bin = self._q2bin,
            d_nll = { self._reg : cfg_nll },
            cfg   = self._mod_cfg)
        res = ftr.run()

        self._save_fit(
            data    = cfg_nll.nll.data[0],   # Likelihood factory makes NLL for one single region
            model   = cfg_nll.nll.model[0],  # Pick the data and model for that region
            cut_cfg = cfg_nll.selection,
            res     = res, 
            out_path= self._out_path,
            plt_cfg = self._mod_cfg.plots[self._q2bin].regions[self._reg],
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
            res = self.__fit_cr()

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
