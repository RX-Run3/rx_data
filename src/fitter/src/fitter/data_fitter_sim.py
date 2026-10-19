'''
Module containing DataFitterSim class
'''
from typing          import Literal
from typing          import overload
from dmu             import LogStore, LogLevels
from dmu.stats       import FitResult
from dmu.stats       import zfit
from dmu.stats       import utilities as sut
from dmu.generic     import utilities as gut
from rx_common       import Qsq, Region
from zfit.exception  import ParamNameNotUniqueError
from zfit.loss       import ExtendedUnbinnedNLL as NLL

from .likelihood_factory import NLLConf
from .base_fitter        import BaseFitter
from .configs            import RXFitConfig

log=LogStore.add_logger('fitter:data_fitter_sim')
# ----------------------
class DataFitterSim(BaseFitter):
    '''
    Class meant to take likelihoods for different regions
    when the regions switch channels and projects
    and fitting configuration, e.g. constraints and:

    - Build single likelihood with proper constraints
    - Minimize it
    - Save results including plots
    '''
    # ----------------------
    def __init__(
        self,
        q2bin : Qsq,
        d_nll : dict[Region,     NLLConf],
        d_cfg : dict[Region, RXFitConfig]) -> None:
        '''
        Parameters
        -------------
        q2bin: E.g. central
        d_nll: Dictionary with:
            Key  : Name of region where to fig, e.g. signal, control
            Value:
                - ExtendedBinnedNLL instance
                - Configuration storing the selections used by default and in the fit
        d_cfg: Dictionary mapping fitting region to config 
        '''
        self._q2bin   = q2bin
        self._d_nll   = d_nll
        self._d_cfg   = d_cfg

        BaseFitter.__init__(self)
    # ----------------------
    def _get_full_nll(self) -> NLL:
        '''
        Returns
        -------------
        Full likelihood, i.e. sum over all the models
        '''
        l_nll = [ cfg.nll for cfg in self._d_nll.values() ]
        try:
            nll = gut.add_container(l_nll)
        except ParamNameNotUniqueError as exc:
            for nll in l_nll:
                pdf = nll.model[0]
                sut.print_pdf(pdf=pdf, level=LogLevels.error)

            raise ParamNameNotUniqueError('Models contain multiple parameters with the same name') from exc

        return nll
    # ----------------------
    def _minimize_nll(self, nll : NLL) -> FitResult:
        '''
        Parameters
        ---------------
        nll: Full likelihood

        Returns
        ---------------
        Fit result
        '''
        minimizer     = zfit.minimize.Minuit()
        res           = minimizer.minimize(loss = nll)
        res.hesse(name='minuit_hesse', method = 'minuit_hesse')

        try:
            fres = FitResult.from_zfit(res = res)
        except Exception as exc:
            path = sut.save_nll(loss = nll)
            raise ValueError(
                f'Failed to transform zfit result to FitResult, nll saved to: {path}'
            ) from exc

        return fres
    # ---------------------------------------------
    def _save_by_region(
        self, 
        reg  : Region,
        nll  : NLLConf, 
        cfg  : RXFitConfig,
        fres : FitResult) -> None:
        '''
        Parameters
        ----------------
        reg : Fitting region
        nll : Likelihood for all regions, merged
        cfg : Configuration for region
        fres: Fit result object
        '''
        out_dir = cfg.output_directory / reg.name
        self._save_fit(
            cut_cfg  = nll.selection,
            plt_cfg  = cfg.mod_cfg.plots[self._q2bin].regions[reg],
            data     = nll.nll.data[0],
            model    = nll.nll.model[0],
            res      = fres,
            out_path = out_dir)

        out_path = out_dir / 'conf.yaml'
        log.info(f'Saving configuration to: {out_path}')
        cfg.mod_cfg.to_yaml(path = out_path)

        out_path = out_dir / 'nll_fitted.bytes'
        log.info(f'Saving NLL to: {out_path}')
        sut.save_nll(loss = nll.nll, path = out_path)
    # ----------------------
    @overload
    def run(self, skip_fit: Literal[True]) -> None: ...
    @overload
    def run(self, skip_fit: Literal[False])-> FitResult: ...
    def run(self, skip_fit: bool) -> FitResult | None:
        '''
        Parameters
        -------------
        skip_fit: If true will do an early return (of None) just before fit

        Returns
        -------------
        Fit result
        '''
        nll = self._get_full_nll()

        if skip_fit:
            return None

        fres = self._minimize_nll(nll = nll)

        for region in self._d_nll:
            nll_cfg = self._d_nll[region]
            cfg     = self._d_cfg[region]

            self._save_by_region(
                reg = region,
                nll = nll_cfg, 
                cfg = cfg,
                fres= fres,
            )

        return fres
# ----------------------
