'''
Module holding Calculator class
'''
import pandas as pnd

from dmu.stats     import zfit
from dmu.stats     import FitResult
from typing        import overload
from dmu           import LogStore
from dmu.stats     import Constraints
from dmu.stats     import utilities as sut
from fitter        import ToyConf, ToyMaker

Nll    = zfit.loss.ExtendedUnbinnedNLL
zpdf   = zfit.pdf
zloss  = zfit.loss
zparam = zfit.param

log    = LogStore.add_logger('rx_stats:systematics')
# ------------------------------------
class Calculator[PDF : zpdf.BasePDF ]:
    '''
    Class meant to:

    - Pick NLL
    - Use it alongside alternative fitting models to make toys and fit them
    - Return pandas dataframe with fitting parameters
    '''
    # ----------------------
    def __init__(
        self,
        poi : str,
        nll : Nll,
        res : FitResult,
        cns : Constraints,
        cfg : ToyConf):
        '''
        Parameters
        ---------------
        poi : Parameter of interest
        nll : Holder of likelihoods for each channel or likelihood for given channel
        res : Zfit result object with result of fit to real data
        cns : Object holding parameter constraints
        cfg : Config object controlling toy generation
        '''
        self._poi = poi
        self._nll = nll
        self._res = res
        self._cns = cns
        self._cfg = cfg

        # Sampler is made with nominal model.
        # This calculator fits alternative model to toy data from nominal
        # i.e. sampler will be re-used
        self._sam = [ model.create_sampler() for model in self._nll.model ]

        self._df_nom : None | pnd.DataFrame       = None
        self._params : dict[str,zparam.Parameter] = { par.name : par for par in self._nll.get_params(floating = True) }

        if self._poi not in self._params:
            for name in self._params:
                log.error(name)
            raise ValueError(f'POI {poi} not found as floating parameter in NLL')
    # ----------------------
    @overload
    def _make_toys(
        self,
        *,
        label : str,
        res   : None,
        cns   : None,
        nll   : None) -> pnd.DataFrame: ...
    @overload
    def _make_toys(
        self,
        *,
        label : str,
        res   : FitResult,
        cns   : Constraints,
        nll   : Nll) -> pnd.DataFrame: ...
    def _make_toys(
        self,
        *,
        label : str,
        res   : FitResult   | None,
        cns   : Constraints | None,
        nll   : Nll         | None) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        label : Systematic label
        cns   : Constraints

        Returns
        -------------
        DataFrame with fitting parameters
        '''
        # If None passed, use nominal everything, for toys
        # If overriden, use alternative model with nominal data (sampler)
        res = self._res if res is None else res
        cns = self._cns if cns is None else cns
        nll = self._nll if nll is None else nll.create_new(data = self._sam)

        mkr = ToyMaker(
            nll = self._nll,
            cns = self._cns,
            cfg = self._cfg,
            res = self._res)

        df = mkr.get_parameter_information(name = label, samplers = self._sam)

        return df
    # ----------------------
    @property
    def poi(self) -> str:
        '''
        Returns
        ------------
        Parameter of interest
        '''
        return self._poi
    # ----------------------
    @property
    def models(self) -> list[PDF]:
        '''
        Returns
        ------------
        List of nominal models, one per signal region
        '''
        models = self._nll.model
        if not isinstance(models, list):
            raise ValueError('No models found in likelihood')

        return models # type: ignore
    # ----------------------
    @property
    def parameters(self) -> dict[str, zparam.Parameter]:
        '''
        Returns
        ------------
        Dictionary with parameters meant to float in nominal model
        '''
        return self._params
    # ----------------------
    @property
    def df_nom(self) -> pnd.DataFrame:
        '''
        Returns
        -------------
        Pandas dataframe with fitting parameters
        '''
        if self._df_nom is None:
            raise ValueError('Nominal model, fitting parameters not found')

        return self._df_nom
    # ----------------------
    def bootstrap(self, nboot : int, model : str, label : str) -> pnd.DataFrame:
        '''
        Parameters
        ------------
        nboot: Number of times a model is bootstrapped for a given nominal toy data
        model: Model component to be bootstrapped
        label: String used for naming of outputs

        Returns
        ------------
        Dataframe with each row representing a toy sample from nominal model fit
        '''
        l_df = []
        for index in range(nboot):
            nll = self._bootstrap_model(name = model, index = index)
            mkr = ToyMaker(
                nll = nll,
                cns = self._cns,
                cfg = self._cfg,
                res = self._res)

            df = mkr.get_parameter_information(
                name     = f'{label}_b{index:03d}',
                samplers = self._sam)

            df['bts'] = index

            l_df.append(df)

        df = pnd.concat(l_df)

        return self._merge_bootstrapped_pars(df = df)
    # ----------------------
    def _bootstrap_model(self, name : str, index : int) -> Nll:
        '''
        Parameters
        --------------
        name : Name of component model to be bootstrapped in nominal likelihood
        index: Index used to calculate random seed

        Return
        --------------
        Tuple with:
        - Nominal likelihood with model replaced with bootstrapped version
        - Sampler associated to KDE that needs bootstrapping
        '''
        # Need a copy of the list of models to dissentable
        # bootstrapped NLL from original one
        models = [ model for model in self._nll.model ]
        pdf    = sut.find_model(
            models = models,
            name   = name)

        pdf   = sut.bootstrap_kde(pdf = pdf, index = index)
        models= sut.replace_model(
            models = models,
            name   = name,
            pdf    = pdf)

        nll = self._nll.create_new(model = models)

        return nll
    # ----------------------
    def _merge_bootstrapped_pars(self, df : pnd.DataFrame) -> pnd.DataFrame:
        '''
        Parameters
        ----------------
        df: DataFrame with bootstrapping column added ('bts') to keep track of fits
            to bootstrapped models

        Returns
        ----------------
        Dataframe where the parameters are the median of the bootsrapped parameters
        output should contain columns:

        ['Parameter', 'Value', 'Error', 'Gen', 'Toy', 'GOF']
        '''
        df    = df[df['Valid'] == 1]
        group = df.groupby(by = ['Toy', 'Parameter'])
        df    = group[['Value', 'Error', 'GOF', 'Gen']].median()
        df    = df.reset_index(inplace = False)

        return df
    # ----------------------
    def switch_model(
        self,
        nll   : Nll,
        cns   : Constraints,
        res   : FitResult,
        label : str) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        nll    : Alternative model likelihood
        cns    : Object holding constraints, under alternative model
        res    : Fit result associated to real data fit to alternative model
        label  : Label for model, used for naming outputs, meant to be systematic, e.g. sig_dscb

        Returns
        -------------
        Dataframe with fit parameters, with each row corresponding to one toy
        '''
        log.info(30 * '-')
        log.info(f'Making toys for \"{label}"')
        log.info(30 * '-')
        df = self._make_toys(
            nll   = nll,
            res   = res,
            cns   = cns,
            label = label)

        return df
    # ----------------------
    def make_toys(self) -> pnd.DataFrame:
        '''
        Returns
        -------------
        Dataframe with fit parameters, with each row corresponding to one toy
        '''
        log.info(30 * '-')
        log.info('Making nominal toys')
        log.info(30 * '-')
        df = self._make_toys(
            nll   = None,
            res   = None,
            cns   = None,
            label = 'nominal')

        return df
    # ----------------------
    def fix_parameter(
        self,
        name  : str,
        label : str) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        name : Name of parameter to be fixed
        label: Label for model, used for naming outputs, meant to be systematic, e.g. sig_dscb

        Returns
        -------------
        Dataframe with fit parameters, with each row corresponding to one toy
        '''
        param = self._params.get(name)
        if param is None:
            for par_name in self._params:
                log.warning(par_name)
            raise ValueError(f'Cannot find parameter: {name}')

        if not param.floating:
            log.warning(f'Parameter {name} is already fixed')

        log.info(30 * '-')
        log.info(f'Fixing {name}')
        log.info(30 * '-')
        param.floating = False

        df = self._make_toys(
            nll   = None,
            cns   = None,
            res   = None,
            label = label)

        return df
# ------------------------------------
