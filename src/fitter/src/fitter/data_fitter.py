'''
Module containing DataFitter class
'''
from typing          import Final
from pathlib         import Path
from dmu             import LogStore
from dmu.workflow    import Cache
from dmu.stats       import AnealingMinimizer, FitResult, Retries
from dmu.stats       import zfit
from dmu.stats       import utilities as sut
from rx_common       import Component, Qsq, Region
from zfit.exception  import ParamNameNotUniqueError
from zfit.loss       import ExtendedUnbinnedNLL as NLL

from .likelihood_factory import NLLConf
from .base_fitter        import BaseFitter
from .configs            import FitModelConf

log=LogStore.add_logger('fitter:data_fitter')
_MIN_REGIONS_IN_CAT : Final[int] = 2 # Minimum number of signal regions to plot when merging them
# ----------------------
class DataFitter(BaseFitter, Cache):
    '''
    Class meant to take likelihoods for different regions
    and fitting configuration, e.g. constraints and:

    - Build single likelihood with proper constraints
    - Minimize it
    - Save results including plots
    '''
    # ----------------------
    def __init__(
        self,
        q2bin : Qsq,
        d_nll : dict[Region, NLLConf],
        cfg   : FitModelConf) -> None:
        '''
        Parameters
        -------------
        d_nll: Dictionary with:
            Key  : Name of region where to fig, e.g. signal, control
            Value:
                - ExtendedBinnedNLL instance
                - Configuration storing the selections used by default and in the fit
        cfg  : Dictionary with configuration used for fit with:
            - Output directory
            - Fit settings
            - Plotting settings
        '''
        self._q2bin   = q2bin
        self._d_nll   = d_nll
        self._cfg     = cfg
        self._trigger = cfg.trigger

        regions = '_'.join(d_nll)

        BaseFitter.__init__(self)
        # TODO: Is the likelihood hashable?
        # If so, it should be here
        Cache.__init__(
            self,
            out_path = Path(Component.data_24) / 'fit' / regions,
            cfg      = cfg.model_dump())
    # ----------------------
    def _get_full_nll(self) -> NLL:
        '''
        Returns
        -------------
        Full likelihood, i.e. sum over all the models
        '''
        l_nll = [ cfg.nll for cfg in self._d_nll.values() ]
        try:
            nll   = sum(l_nll[1:], l_nll[0])
        except ParamNameNotUniqueError as exc:
            for nll in l_nll:
                pdf = nll.model[0]
                sut.print_pdf(pdf=pdf)

            raise ParamNameNotUniqueError('Models contain multiple parameters with the same name') from exc

        return nll
    # ----------------------
    def _save_config(self, out_dir : Path) -> None:
        '''
        Parameters
        -------------
        out_dir: Path to output directory
        '''
        out_path= out_dir / 'conf.yaml'
        log.info(f'Saving configuration to: {out_path}')
        self._cfg.to_yaml(path = out_path)
    # ----------------------
    def _simple_fit(self, nll : NLL) -> FitResult:
        '''
        Parameters
        -------------
        nll: Likelihood

        Returns
        -------------
        Fit result
        '''
        minimizer = zfit.minimize.Minuit()
        res = minimizer.minimize(loss = nll)                            # type: ignore[reportUnknownMemberType]
        res.hesse(name='minuit_hesse', method = 'minuit_hesse')   # type: ignore[reportUnknownMemberType]

        try:
            fres = FitResult.from_zfit(res = res)
        except Exception as exc:
            path = sut.save_nll(loss = nll)
            raise ValueError(
                f'Failed to transform zfit result to FitResult, nll saved to: {path}'
            ) from exc

        return fres
    # ---------------------------------------------
    def _minimize_nll(self, nll : NLL) -> FitResult:
        '''
        Parameters
        ---------------
        nll: Full likelihood

        Returns
        ---------------
        Fit result
        '''
        if   self._cfg.fit.strategy is None:
            fres = self._simple_fit(nll = nll)
        elif isinstance(self._cfg.fit.strategy, Retries):
            minimizer  = AnealingMinimizer(cfg = self._cfg.fit)
            fres = minimizer.get_result(loss = nll)
        else:
            raise NotImplementedError(f'Invalid strategy: {self._cfg.fit.strategy}')

        return fres
    # ---------------------------------------------
    def _save_merged_regions(
        self, 
        region  : Region, 
        fres    : FitResult,
        regions : list[Region]) -> None:
        '''
        Parameters
        ---------------
        region : Merged region 
        fres   : Fit result
        regions: List of regions associated
        '''
        if len(regions) < _MIN_REGIONS_IN_CAT:
            raise ValueError(f'Cannot create category with fewer than two regions, found: {regions}')

        out_path = self._out_path / region 

        log.info(f'Saving fit to: {out_path}')

        nlls     = [ cfg.nll for region, cfg in self._d_nll.items() if region in regions ]
        datasets = [ nll.data[0]  for nll in nlls ]

        models : list[zfit.pdf.SumPDF]  = []
        for nll in nlls:
            pdf = nll.model[0]
            if not isinstance(pdf, zfit.pdf.SumPDF):
                raise ValueError('Found non SumPDF model')

            models.append(pdf)

        # Model names start with component, i.e. bpkpee_bremxx1...
        # Extract component names and use them as preffix to merge pdfs
        # In order to plot combined model
        prefixes : list[Component] = [ component for component in self._cfg.components[self._q2bin] ]
        model = sut.merge_sum_models(
            obs      = self._cfg.obs, 
            models   = models, 
            prefixes = prefixes,
            pair     = 'by_prefix')

        self._save_fit(
            cut_cfg  = dict(),
            plt_cfg  = self._cfg.plots[self._q2bin].regions[region],
            data     = zfit.data.concat(datasets),
            model    = model,
            res      = fres,
            out_path = out_path)
    # ---------------------------------------------
    def _save_by_region(
        self, 
        nll  : NLL, 
        fres : FitResult) -> None:
        '''
        Parameters
        ----------------
        nll : Likelihood for all regions, merged
        fres: Fit result object
        '''
        l_sel  = [ cfg.selection for cfg in self._d_nll.values() ]
        l_reg  = list(self._d_nll)

        sut.save_nll(loss = nll, path = self._out_path / 'nll.bytes')

        for model, data, sel, region in zip(nll.model, nll.data, l_sel, l_reg, strict = True):
            out_path = self._out_path / region

            log.info(f'Saving fit to: {out_path}')

            self._save_fit(
                cut_cfg  = sel,
                plt_cfg  = self._cfg.plots[self._q2bin].regions[region],
                data     = data,
                model    = model,
                res      = fres,
                out_path = out_path)

            self._save_config(out_dir=out_path)
    # ----------------------
    def run(self) -> FitResult:
        '''
        Parameters
        -------------
        fit_cfg: Fit configuration.

        Returns
        -------------
        Fit result
        '''
        result_path = self._out_path / 'parameters.json'
        if self._copy_from_cache():
            fres = FitResult.from_json(path = result_path)
            return fres

        nll = self._get_full_nll()
        if nll is None:
            raise ValueError('Likelihood is missing')

        fres = self._minimize_nll(nll = nll)

        self._save_by_region(nll = nll, fres = fres)

        fres.to_json(path = result_path)

        # If there is one signal region (fit is not simultaneous)
        # we can skip making plot of merged signal regions 
        if len(self._d_nll) == 1:
            self._cache()
            return fres

        for cat, regions in self._cfg.plots[self._q2bin].merging.items():
            self._save_merged_regions(
                region  = cat, 
                fres    = fres,
                regions = regions)

        self._cache()

        return fres
# ----------------------
