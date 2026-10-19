'''
Module holding Calculator class
'''
import pandas as pnd

from dmu.stats     import zfit
from dmu.stats     import FitResult
from zfit.data     import SamplerData
from typing        import Literal
from dmu           import LogStore
from dmu.stats     import Constraints
from fitter        import ToyConf, ToyMaker
from fitter        import ChannelHolder

Nll    = zfit.loss.ExtendedUnbinnedNLL
pdf    = zfit.pdf
loss   = zfit.loss
param  = zfit.param

log    = LogStore.add_logger('rx_stats:systematics')
Channel= Literal['mm', 'ee']
# ------------------------------------
class Calculator[PDF : pdf.BasePDF ]:
    '''
    Class meant to:

    - Pick NLL
    - Use it alongside alternative fitting models to make toys and fit them
    - Return pandas dataframe with fitting parameters
    '''
    # ----------------------
    def __init__(
        self,
        obj  : ChannelHolder[Nll] | Nll,
        poi  : str,
        res  : FitResult,
        cfg  : ToyConf):
        '''
        Parameters
        ---------------
        nll  : Holder of likelihoods for each channel or likelihood for given channel
        poi  : Parameter of interest
        res  : Zfit result object with result of fit to real data
        rseed: Random seed for current toys
        '''
        self._obj = obj
        self._nll = obj if isinstance(obj, Nll) else obj.mm + obj.ee
        self._poi = poi
        self._res = res
        self._cfg = cfg
        # Sampler is made with nominal model.
        # This calculator fits alternative model to toy data from nominal
        # i.e. sampler will be re-used
        self._sam = [ self._sampler_from_model(model = model) for model in self._nll.model ]

        self._df_nom : None | pnd.DataFrame      = None
        self._params : dict[str,param.Parameter] = { par.name : par for par in self._nll.get_params(floating = True) }

        if self._poi not in self._params:
            for name in self._params:
                log.error(name)
            raise ValueError(f'POI {poi} not found as floating parameter in NLL')
    # ----------------------
    def _sampler_from_model(self, model : pdf.BasePDF) -> SamplerData:
        '''
        Parameters
        -------------
        model : Zfit PDF

        Returns
        -------------
        Sampler corresponding to argument PDF
        '''
        sampler            = model.create_sampler()
        setattr(sampler, model.name, 'model_name')

        return sampler
    # ----------------------
    def _make_toys(
        self,
        label   : str,
        model   : pdf.SumPDF | None,
        channel : Channel| None) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        label   : Systematic label
        model   : Dictionary mapping channel to PDF that needs to be switched
        channel : ee or mm, needed to

        Returns
        -------------
        DataFrame with fitting parameters
        '''
        cns = Constraints.none()
        nll = self._get_new_nll(model = model, channel = channel)

        mkr = ToyMaker(
            nll = nll,
            cns = cns,
            cfg = self._cfg,
            res = self._res)

        df = mkr.get_parameter_information(name = label, samplers = self._sam)

        return df
    # ----------------------
    def _get_new_nll(
        self,
        model  : pdf.SumPDF | None,
        channel: Channel| None) -> loss.ExtendedUnbinnedNLL:
        '''
        Parameters
        -------------
        model  : Replacement model, if None, will use nominal model to make toys
        channel: Channel where the model will be replaced, if non-simultaneous fit, channel will be None

        Returns
        -------------
        NLL after model replacement
        '''
        if model is None:
            log.debug('Using nominal model')
            return self._nll

        if isinstance(self._obj, loss.ExtendedUnbinnedNLL) and isinstance(model, pdf.SumPDF):
            log.debug('Found NLL for non-simultaneous fit, replacing model')
            return self._obj.create_new(model = model)

        if channel is None:
            raise ValueError('Channel not specified but using multichannel likelihood')

        if isinstance(self._obj, ChannelHolder) and isinstance(model, pdf.SumPDF):
            other_channel = 'ee' if channel == 'mm' else 'mm'
            nll_other     = getattr(self._obj, other_channel)

            nll_this : loss.ExtendedUnbinnedNLL = getattr(self._obj,       channel)
            nll_new = nll_this.create_new(model = model)

            return nll_new + nll_other

        raise ValueError(f'Cannot retrieve new NLL for channel {channel}')
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
    def parameters(self) -> dict[str, param.Parameter]:
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
    def switch_model(
        self,
        label  : str,
        model  : pdf.SumPDF | None,
        channel: Channel | None = None) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        label  : Label for model, used for naming outputs, meant to be systematic, e.g. sig_dscb
        model  : Alternative model to do fits with. If None, will use nominal model
        channel: When using simultaneous fits, this will define signal region where replacement will be made

        Returns
        -------------
        Dataframe with fit parameters, with each row corresponding to one toy
        '''
        log.info(30 * '-')
        log.info(f'Making toys for \"{label}" model in channel: \"{channel}\"')
        log.debug(model)
        log.info(30 * '-')
        df = self._make_toys(
            model   = model,
            label   = label,
            channel = channel)

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
        else:
            log.info(30 * '-')
            log.info(f'Fixing {name}')
            log.info(30 * '-')
            param.floating = False

        df = self._make_toys(
            model   = None,
            channel = None,
            label   = label)

        return df
# ------------------------------------
