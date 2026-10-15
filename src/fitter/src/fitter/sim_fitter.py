'''
Module with SimFitter class
'''
import os

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from pathlib             import Path
from typing              import overload, Literal, Final
from dmu                 import LogStore
from dmu.stats           import FitResult, ModelFactoryConf
from dmu.stats           import ModelFactory
from dmu.stats           import utilities        as sut
from dmu.workflow        import Cache

from rx_common           import Correction, Qsq, Trigger, Component, Cuts
from rx_selection        import selection        as sel

from zfit.data           import Data             as zdata
from zfit.pdf            import BasePDF          as zpdf
from zfit.param          import Parameter

from .category           import Category, FitCategory
from .category_merger    import CategoryMerger, FitCategoryMerger
from .base_fitter        import BaseFitter
from .configs            import CombinatorialConf, CombinatorialConfUnconstrained, MisIDConf, NonParametricConf, ParametricConf, CCbarConf, AnyModelConf
from .data_preprocessor  import DataPreprocessor
from .prec               import PRec

log=LogStore.add_logger('fitter:sim_fitter')

# Will not build (fit) a parametric PDF if fewer than these entries
# will return None
_MIN_FIT_ENTRIES : Final[int] = 100

# Will not build KDE if fewer than these entries in dataset
_MIN_KDE_ENTRIES : Final[int] = 50
# ------------------------
class SimFitter(BaseFitter, Cache):
    '''
    Fitter for simulation samples
    '''
    # ------------------------
    def __init__(
        self,
        name      : str,
        component : Component,
        trigger   : Trigger,
        q2bin     : Qsq,
        cfg       : AnyModelConf):
        '''
        Parameters
        --------------------
        name     : Fit identifier, e.g. bkpp, control, signal
        component: Nickname of component, e.g. combinatorial, only used for naming
        trigger  : Hlt2RD...
        q2bin    : E.g. central
        cfg      : Object storing configuration for fit
        '''
        BaseFitter.__init__(self)
        log.info(20 * '-')
        log.info(f'Fitting {component}')
        log.info(20 * '-')

        self._component = component
        self._trigger   = trigger
        self._q2bin     = q2bin
        self._cfg       = cfg
        self._name      = name

        self._l_rdf_uid : list[str] = []
        self._d_data    = self._get_data()

        Cache.__init__(
            self,
            out_path = Path(self._component) / 'fit' / name,
            l_rdf_uid= self._l_rdf_uid,
            config   = self._cfg.model_dump())
    # ------------------------
    # Data getting section
    # ------------------------
    def _get_data(self) -> dict[str,zdata]:
        '''
        Returns
        --------------------
        dictionary with:

        Key  : Name of MC category, e.g. brem category
        Value: Zfit dataset
        '''
        # Combinatorial does not have MC to fix tails
        # Constrained combinatorial will pick constraints from separate fit
        # CCbar will be fitted using PRec class, which will pick data
        SkipDataConf = CombinatorialConf | CombinatorialConfUnconstrained | CCbarConf

        if isinstance(self._cfg, SkipDataConf):
            return dict() 

        if isinstance(self._cfg, ParametricConf):
            return self._get_category_data(cfg = self._cfg)

        if isinstance(self._cfg, NonParametricConf):
            return self._get_nonparametric_data(cfg = self._cfg)

        raise ValueError(f'Cannot get data for: {type(self._cfg)}')
    # ------------------------
    def _get_category_data(self, cfg : ParametricConf) -> dict[str,zdata]:
        '''
        Parameters
        --------------
        cfg: Object storing configuration

        Returns
        --------------
        Dictionary mapping category name (e.g. brem_xx1_b3) to corresponding
        zfit data object
        '''
        d_data : dict[str, zdata] = {}
        log.info('Retrieving category data')
        for cat_name, cat_cfg in cfg.categories.items():
            log.info(f'    {cat_name}')

            prp = DataPreprocessor(
                name      = cat_name,
                wgt_cfg   = dict(),
                obs       = self._cfg.obs,
                trigger   = self._trigger,
                q2bin     = self._q2bin,
                selection = cat_cfg.selection,
                sample    = cfg.component)

            d_data[cat_name] = prp.get_data()

            self._l_rdf_uid.append(prp.rdf_uid)

        return d_data
    # ------------------------
    def _get_nonparametric_data(self, cfg : NonParametricConf) -> dict[str,zdata]:
        '''
        Parameters
        --------------
        cfg: Object storing configuration
        '''
        if isinstance(cfg, MisIDConf):
            wgt_cfg = {Correction.pid : cfg.weights}
            cut     = cfg.selection
            log.debug(f'Overriding cuts {cut} and using weights')
        else:
            wgt_cfg = None
            cut     = None
            log.debug('Not overriding cuts or using weights')

        d_data : dict[str, zdata] = {}
        prp   = DataPreprocessor(
            wgt_cfg   = wgt_cfg,
            obs       = cfg.obs,
            trigger   = self._trigger,
            q2bin     = self._q2bin,
            selection = cut,
            name      = self._name,
            sample    = cfg.component)

        d_data[self._name] = prp.get_data()

        self._l_rdf_uid.append(prp.rdf_uid)

        return d_data
    # ------------------------
    # PDF getting section
    # ------------------------
    def _get_pdf(
        self,
        cfg     : ModelFactoryConf,
        category: str) -> zpdf:
        '''
        Parameters
        ------------
        category: If the MC is meant to be split (e.g. by brem) this should the the label of the category
        cfg     : Configuration needed to build model

        Returns
        ------------
        Fitting PDF built from the sum of those models
        '''
        log.info(f'Building {self._component} for category {category} with: {cfg.pdfs}')

        mod         = ModelFactory(
            preffix = f'{self._component}_{category}',
            obs     = self._cfg.obs,
            l_pdf   = cfg.pdfs,
            l_reuse = cfg.reuse,
            l_shared= cfg.shared,
            l_float = cfg.floating ,
            values  = cfg.values,
            d_rep   = cfg.reparametrize,
            d_fix   = cfg.fix)

        pdf = mod.get_pdf()

        return pdf
    # ------------------------
    def _fix_tails(self, pdf : zpdf, res : FitResult) -> zpdf:
        '''
        Parameters
        --------------
        pdf : PDF after fit
        res : Fit result object, used to fix tails

        Returns
        --------------
        PDF with tails fixed to values in `res` and non-fixed parameters floating
        '''
        s_par = pdf.get_params(floating = True) | pdf.get_params(floating=False)
        npar  = len(s_par)
        log.debug(f'Found {npar} parameters')

        for par in s_par:
            # Model builder adds _flt to name
            # of parameters meant to float
            if par.name.endswith('_flt'):
                log.debug(f'Not fixing: {par.name}')
                par.floating = True 
                continue

            if par.name in res:
                val, _ = res[par.name]

                par.set_value(val)
                log.debug(f'{par.name:<20}{"--->"}{val:>20.3f}')
                par.floating = False

        return pdf
    # ------------------------
    def _get_nomc_pdf(
        self,
        cfg : CombinatorialConf | CombinatorialConfUnconstrained) -> zpdf:
        '''
        Returns
        -------------
        PDF for component that does not require MC, e.g. combinatorial
        '''
        if self._q2bin not in cfg.models:
            for val in cfg.models:
                log.error(val)
            raise ValueError(f'Bin {self._q2bin} not found')

        model_cfg = cfg.models[self._q2bin]
        model     = self._get_pdf(
            cfg     = model_cfg,
            category= self._name)

        return model
    # ------------------------
    # Fitting section
    # ------------------------
    @overload
    def _get_fit_category(
        self,
        cfg      : ParametricConf,
        skip_fit : Literal[False],
        name     : str) -> FitCategory | None : ...
    @overload
    def _get_fit_category(
        self,
        cfg      : ParametricConf,
        skip_fit : Literal[True],
        name     : str) -> Category: ...
    def _get_fit_category(
        self,
        cfg      : ParametricConf,
        skip_fit : bool,
        name     : str) -> FitCategory | Category | None:
        '''
        Parameters
        ----------------
        skip_fit : If true, it will only return model, used if fit parameters were already found
        name     : Name of fitting category

        Returns
        ----------------
        FitCategory: Fit was requested and fit worked
        Category   : Fit was not requested
        None       : Fit was requested but it failed
        '''
        log.info(f'Fitting category {name}')

        cat_cfg = cfg.categories[name]
        model = self._get_pdf(
            category= name,
            cfg     = cat_cfg.model)

        data  = self._d_data[name]

        sumw  = sut.yield_from_zdata(data=data)

        if skip_fit:
            return Category(
                name      = name, 
                pdf       = model, 
                sumw      = sumw,
                model     = cat_cfg.model.pdfs,
                selection = cat_cfg.selection)

        cut_cfg = self._get_cut_config(cfg = cfg, category = name)

        if sumw < _MIN_FIT_ENTRIES:
            log.warning(f'Found to few entries {sumw:.1f} < {_MIN_FIT_ENTRIES}, skipping {self._component} component')
            self._save_fit(
                cut_cfg  = cut_cfg,
                plt_cfg  = cfg.plots,
                data     = data,
                model    = None,
                res      = None,
                out_path = self._out_path / name )

            return None 

        res = self._fit(
            data = data, 
            model= model, 
            cfg  = cfg.fit)

        self._save_fit(
            cut_cfg  = cut_cfg,
            plt_cfg  = cfg.plots,
            data     = data,
            model    = model,
            res      = res,
            out_path = self._out_path / name)

        model = self._fix_tails(pdf=model, res=res)

        return FitCategory(
            name      = name,
            pdf       = model,
            sumw      = sumw,
            res       = res,
            model     = cat_cfg.model.pdfs,
            selection = cat_cfg.selection)
    # ----------------------
    def _get_cut_config(
        self, 
        category : str | None,
        cfg      : ParametricConf | NonParametricConf) -> dict[str,dict[Cuts,str]]:
        '''
        Parameters
        -------------
        category: Fit category, e.g. brem_xx1 or None, if it does not make sense, e.g. KDE fits

        Returns
        -------------
        Dictionary with:
            Keys  : `fit`, `default`
            Values: Selection for data that was fitted and default
        '''
        cuts_current= sel.selection(
            process = cfg.component, 
            trigger = self._trigger, 
            q2bin   = self._q2bin)

        if isinstance(cfg, ParametricConf) and category is not None:
            fit_cuts = cfg.categories[category].selection
            cuts_current.update(fit_cuts)

        cuts = {'fit' : cuts_current}

        with sel.custom_selection(d_sel={}, force_override=True):
            cuts['default'] = sel.selection(
                process = cfg.component, 
                trigger = self._trigger, 
                q2bin   = self._q2bin)

        return cuts
    # ------------------------
    # TODO: Fractions need to be parameters to be constrained
    def _get_fraction(
        self,
        sumw     : float,
        total    : float,
        category : str) -> Parameter:
        '''
        Parameters
        -------------
        sumw    : Yield in MC associated to this category
        total   : Total yield
        category: Name of this category

        Returns
        -------------
        Fitting fraction parameter fixed
        '''
        frac_name = f'frac_{self._component}_{category}'
        value     = sumw / total
        par       = Parameter(frac_name, value, 0, 1)

        log.debug(f'{frac_name:<50}{value:<10.3f}')

        return par
    # ------------------------
    @overload
    def _get_merged_category(
        self, 
        cfg      : ParametricConf, 
        skip_fit : Literal[True]) -> Category: ...
    @overload
    def _get_merged_category(
        self, 
        cfg      : ParametricConf, 
        skip_fit : Literal[False]) -> FitCategory | None: ...
    def _get_merged_category(
        self, 
        cfg      : ParametricConf, 
        skip_fit : bool) -> FitCategory | Category | None:
        '''
        Parameters
        ---------------
        cfg     : Configuration for fits to parametric PDFs
        skip_fit: If true, it will rturn the model without fitting

        Returns
        ---------------
        Category    If fit is not requested
        FitCategory If fit was requested and succeeded
        None        If fit was requested and failed for all categories
        '''
        cats_fit : list[FitCategory] = []
        cats_raw : list[Category]    = []
        for name in cfg.categories:
            cat = self._get_fit_category(
                cfg      = cfg,
                skip_fit = skip_fit,
                name     = name)

            if cat is None:
                log.warning(f'Skipping category {name}')
                continue

            if isinstance(cat, FitCategory):
                cats_fit.append(cat)
            else:
                cats_raw.append(cat)

        cats = cats_fit + cats_raw
        if len(cats) == 1:
            return cats[0]

        if len(cats) == 0:
            log.warning('No categories found, dropping component')
            return None

        if skip_fit:
            mgr = CategoryMerger(
                reparametrize = self._q2bin.is_rare,
                categories    = cats_raw, 
                comp          = self._component)
        else:
            mgr = FitCategoryMerger(
                reparametrize = self._q2bin.is_rare,
                categories    = cats_fit, 
                comp          = self._component)

        cat = mgr.get_category()

        return cat
    # ------------------------
    def _get_kde(self, cfg : NonParametricConf) -> zpdf | None:
        '''
        KDE is not fit in categories, there is just a MAIN_CATEGORY

        - Makes KDE PDF
        - Saves fit (plot, list of parameters, etc)

        Parameters
        ------------------
        cfg: Configuration for KDE

        Returns
        ------------------
        - KDE PDF after fit
        - None if there are fewer than _min_kde_entries
        '''

        data     = self._d_data[self._name]
        nentries = self._entries_from_data(data = data, obs = self._cfg.obs)
        if nentries < _MIN_KDE_ENTRIES:
            log.warning(f'Not bulding KDE, found too few entries: {nentries} < {_MIN_KDE_ENTRIES}')
            return 

        pdf = cfg.fit.kind.cls(
            data      = data, 
            name      = f'{self._component}_{self._name}', 
            obs       = cfg.obs, 
            norm      = cfg.norm,
            bandwidth = cfg.fit.bandwidth,
            padding   = cfg.fit.padding.value)

        data_observed = data.with_obs(obs = self._cfg.obs)

        self._save_fit(
            cut_cfg  = self._get_cut_config(cfg = cfg, category = None),
            plt_cfg  = cfg.plots,
            data     = data_observed,
            model    = pdf,
            res      = None,
            out_path = self._out_path)

        return pdf
    # ------------------------
    def _get_ccbar_component(
        self,
        cfg : CCbarConf) -> zpdf | None:
        '''
        This is an interace to the PRec class, which is in
        charge of building the KDE for ccbar sample

        Parameters
        -------------------
        cfg: Configuration

        Returns
        ----------------
        Either:

        - PDF with KDEs added corresponding to different groups of ccbar decays
        - None, if no data was found
        '''
        ftr=PRec(
            obs     = cfg.obs,
            name    = self._name,
            trig    = self._trigger,
            q2bin   = self._q2bin  ,
            cfg     = cfg)

        pdf =ftr.get_sum(name = r'$c\bar{c}+X$')

        return pdf
    # ------------------------
    def get_model(self) -> zpdf | None: # noqa: PLR0911
        '''
        Returns
        ------------
        Either:

        - zfit PDF, not extended yet
        - None, if statistics are too low to build PDF

        Returned PDF needs to have parameters fixed unless
        their names end on _flt. E.g. 

        - Will fix tails, means and widths
        - Will float scales and resolutions
        '''
        if isinstance(self._cfg, CCbarConf):
            return self._get_ccbar_component(cfg = self._cfg)

        if isinstance(self._cfg, (CombinatorialConf, CombinatorialConfUnconstrained)):
            return self._get_nomc_pdf(cfg = self._cfg)

        if isinstance(self._cfg, NonParametricConf):
            return self._get_kde(cfg = self._cfg)

        if not isinstance(self._cfg, ParametricConf):
            raise ValueError(f'Config not a parametric one: {type(self._cfg)}')

        result_path = self._out_path / 'parameters.json'
        if self._copy_from_cache():
            res = FitResult.from_json(path = result_path)

            # If caching, need only model, second return value
            # Is None because no fit happened 
            cat = self._get_merged_category(skip_fit=True, cfg = self._cfg)
            return self._fix_tails(pdf=cat.pdf, res=res)

        log.info(f'Fitting, could not find cached parameters in {result_path}')

        cat = self._get_merged_category(skip_fit=False, cfg = self._cfg)
        if cat is None:
            return None

        cat.res.to_json(path = result_path)

        self._cache()
        return self._fix_tails(pdf=cat.pdf, res=cat.res)
# ------------------------
