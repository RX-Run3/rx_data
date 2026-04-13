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
from rx_common       import Component, Qsq, Region, Cuts
from zfit.exception  import ParamNameNotUniqueError
from zfit.result     import FitResult           as zres
from zfit.loss       import ExtendedUnbinnedNLL as NLL

from .base_fitter    import BaseFitter
from .configs        import FitModelConf

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
        d_nll : dict[Region,tuple[NLL,dict[str,dict[Cuts,str]]]],
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
        l_nll = [ nll for nll, _ in self._d_nll.values() ]
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
    def _simple_fit(self, nll : NLL) -> zres:
        '''
        Parameters
        -------------
        nll: Likelihood

        Returns
        -------------
        Fit result
        '''
        min = zfit.minimize.Minuit()
        res = min.minimize(loss = nll)
        res.hesse(name='minuit_hesse', method = 'minuit_hesse')

        return res
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
        result_path = self._out_path / 'parameters.yaml'
        if self._copy_from_cache():
            fres = FitResult.from_json(path = result_path)
            return fres

        nll = self._get_full_nll()
        if nll is None:
            raise ValueError('Likelihood is missing')

        fres = self._minimize_nll(nll = nll)

        self._save_by_region(nll = nll, fres = fres)

        for cat, regions in self._cfg.plots.merging.items():
            self._save_by_category(
                name    = cat, 
                fres    = fres,
                regions = regions)

        fres.to_json(path = result_path)
        self._cache()

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
            res  = self._simple_fit(nll = nll)
            fres = FitResult.from_zfit(res = res)
        elif isinstance(self._cfg.fit.strategy, Retries):
            min  = AnealingMinimizer(cfg = self._cfg.fit)
            fres = min.get_result(loss = nll)
        else:
            raise NotImplementedError(f'Invalid strategy: {self._cfg.fit.strategy}')

        return fres
    # ---------------------------------------------
    def _save_by_category(
        self, 
        name    : str, 
        fres    : FitResult,
        regions : list[Region]) -> None:
        '''
        Parameters
        ---------------
        name   : Name of category
        fres   : Fit result
        regions: List of regions associated
        '''
        if len(regions) < _MIN_REGIONS_IN_CAT:
            raise ValueError(f'Cannot create category with fewer than two regions, found: {regions}')

        out_path = self._out_path / name 

        log.info(f'Saving fit to: {out_path}')

        nlls = [ nll for region, (nll, _) in self._d_nll.items() if region in regions ]

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
        prefixes : set[str] = { component for component in self._cfg.components }
        model = sut.merge_sum_models(
            obs      = self._cfg.obs, 
            models   = models, 
            prefixes = prefixes,
            pair     = 'by_prefix')

        self._save_fit(
            cut_cfg  = dict(),
            plt_cfg  = self._cfg.plots.regions[name],
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
        l_cfg  = [ cfg for _, cfg in self._d_nll.values() ]
        l_reg  = list(self._d_nll)

        for model, data, cfg, region in zip(nll.model, nll.data, l_cfg, l_reg, strict = True):
            out_path = self._out_path / region

            log.info(f'Saving fit to: {out_path}')

            self._save_fit(
                cut_cfg  = cfg,
                plt_cfg  = self._cfg.plots.regions[region],
                data     = data,
                model    = model,
                res      = fres,
                out_path = out_path)

            self._save_config(out_dir=out_path)
# ----------------------
