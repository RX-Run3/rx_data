'''
Module holding zfitter class
'''
import numpy
import matplotlib.pyplot as plt

from typing          import Protocol
from dmu             import LogStore
from dmu.stats       import ZFitPlotterConf
from zfit.loss       import ExtendedUnbinnedNLL, UnbinnedNLL
from zfit.pdf        import BasePDF       as zpdf
from zfit.param      import Parameter     as zpar
from zfit.data       import Data          as zdat
from zfit            import Space         as zobs

from .               import minimizers
from .imports        import zfit
from .fit_conf       import FitConf, Retries
from .fit_result     import FitResult
from .zfit_plotter   import ZFitPlotter
from .minimizers     import AnealingMinimizer
from .pdf_utilities  import has_gradient
from .utilities      import range_from_obs

log = LogStore.add_logger('dmu:stats:fitter')
Loss= ExtendedUnbinnedNLL | UnbinnedNLL
zcns= zfit.constraint.GaussianConstraint
#------------------------------
class ParameterHolder(Protocol):
    '''
    Class representing object with `get_params` method
    '''
    # ----------------------
    def get_params(self, floating : bool) -> set[zpar]:
        ...
#------------------------------
class FitterFailedFit(Exception):
    '''
    Exception used when fitter fails
    '''
#------------------------------
class Fitter:
    '''
    Class meant to be an interface to underlying fitters
    '''
    #------------------------------
    def __init__(
        self,
        pdf  : zpdf,
        data : zdat | numpy.ndarray):
        '''
        Parameters
        ---------------
        pdf : PDF to fit
        data: Datasets to fit, either zfit data object, or numpy array
        '''
        if not has_gradient(pdf = pdf):
            raise ValueError(f'PDF {pdf.name} has no gradient')

        self._data_in = data
        self._pdf     = pdf
        self._nll     : Loss | None = None

        self._data_zf : zdat
        self._data_np : numpy.ndarray
        self._obs     : zfit.Space

        self._check_data()
    #------------------------------
    def _check_data(self):
        if   isinstance(self._data_in, numpy.ndarray):
            data_np = self._data_in
        elif isinstance(self._data_in, zfit.Data):
            data_np : numpy.ndarray = zfit.run(zfit.z.unstack_x(self._data_in)) # convert original data to numpy array, needed by _calc_gof
        else:
            data_type = str(type(self._data_in))
            raise ValueError(f'Data is not a numpy array, zfit.Data or pandas.DataFrame, but {data_type}')

        data_np       = self._check_numpy_data(data_np)
        self._data_np = data_np
        if not isinstance(self._data_in, zfit.Data):
            data = zfit.Data.from_numpy(obs=self._pdf.space, array=data_np)
            if not isinstance(data, zdat):
                raise ValueError(f'Expected data object, found: {type(data)}')
            self._data_zf = data
        else:
            self._data_zf = self._data_in
    #------------------------------
    def _check_numpy_data(self, data : numpy.ndarray) -> numpy.ndarray:
        shp = data.shape
        if   len(shp) == 1:
            pass
        elif len(shp) == 2: # noqa: PLR2004
            _, jval = shp
            if jval != 1:
                raise ValueError(f'Invalid data shape: {shp}')
        else:
            raise ValueError(f'Invalid data shape: {shp}')

        ival = data.shape[0]

        data = data[~numpy.isnan(data)]
        data = data[~numpy.isinf(data)]

        fval = data.shape[0]

        if ival != fval:
            log.warning(f'Data was trimmed for inf and nan: {ival} -> {fval}')

        return data
    #------------------------------
    def _reshuffle_pdf_pars(self):
        '''
        Will move floating parameters of PDF according
        to uniform PDF
        '''

        s_par : set[zpar] = self._pdf.get_params(floating=True)
        for par in s_par:
            ival = par.value()

            if par.lower is None or par.upper is None:
                raise ValueError(f'Either lower or lower bound missing for: {par.name}')

            fval = numpy.random.uniform(par.lower.numpy(), par.upper.numpy())
            par.set_value(fval)
            log.debug(f'{par.name:<40}{ival:<15.3f}{"->":<10}{fval:<15.3f}{"in":<5}{par.lower:<15.3e}{par.upper:<15.3e}')
    #------------------------------
    def _set_pdf_pars(self, res : FitResult) -> None:
        '''
        Will set the PDF floating parameter values as the result instance
        '''
        l_par_flt = list(self._pdf.get_params(floating= True))
        l_par_fix = list(self._pdf.get_params(floating=False))
        l_par     = l_par_flt + l_par_fix

        log.debug('Setting PDF parameters to best result')
        for par in l_par:
            if par.name not in res:
                log.debug(f'Skipping {par.name} = {par.value().numpy():.3e}')
                continue

            val, _ = res[par.name]
            log.debug(f'{"":<4}{par.name:<20}{"->":<10}{val:<20.3e}')
            par.set_value(val)
    #------------------------------
    def _get_ranges(self, cfg : FitConf) -> list[tuple[float,float]] | None:
        if cfg.ranges is None:
            return None

        ranges_any = cfg.ranges

        ranges = [ elm for elm in ranges_any ]
        log.info('-' * 30)
        log.info(f'{"Low edge":>15}{"High edge":>15}')
        log.info('-' * 30)
        for rng in ranges:
            log.info(f'{rng[0]:>15.3e}{rng[1]:>15.3e}')

        return ranges
    #------------------------------
    def _get_subdataset(self, cfg : FitConf) -> zdat:
        '''
        Returns
        --------------
        Random subset of data in _data_zf with at most cfg['nentries']
        '''
        if cfg.nentries == -1:
            return self._data_zf

        nentries_out = cfg.nentries
        arr_inp      = self._data_zf.to_numpy().flatten()
        nentries_inp = len(arr_inp)
        if nentries_inp <= nentries_out:
            log.warning(f'Input dataset in smaller than output dataset, {nentries_inp} < {nentries_out}')
            return self._data_zf

        has_weights = self._data_zf.weights is not None

        if has_weights:
            arr_wgt = self._data_zf.weights.numpy().flatten()
            arr_inp = numpy.array([arr_inp, arr_wgt], dtype = numpy.float64).T

        arr_out = numpy.random.choice(arr_inp, size=nentries_out, replace=False)
        if has_weights:
            arr_val = arr_out.T[0]
            arr_wgt = arr_out.T[1]
        else:
            arr_val = arr_out
            arr_wgt = None

        data = zfit.data.Data.from_numpy(array=arr_val, weights=arr_wgt, obs=self._data_zf.space)
        if not isinstance(data, zfit.Data):
            raise ValueError('Dataset not unbinned')

        return data
    #------------------------------
    def _get_binned_observable(self, nbins : int):
        obs = self._pdf.space
        if not isinstance(obs, zobs):
            raise ValueError('Observable not an Space instance')

        minx, maxx = range_from_obs(obs = obs)
        binning    = zfit.binned.RegularBinning(nbins, minx, maxx, name=obs.label)
        obs_bin    = zfit.Space(obs.label, binning=binning)

        return obs_bin
    #------------------------------
    def _get_nll(
        self,
        data   : zdat,
        frange : tuple[float,float] | None) -> Loss:

        NLL = zfit.loss.ExtendedUnbinnedNLL if self._pdf.is_extended else zfit.loss.UnbinnedNLL
        nll = NLL(
            model      = self._pdf,
            data       = data,
            fit_range  = frange)

        return nll
    #------------------------------
    def _get_full_nll(self, cfg : FitConf) -> Loss:
        ranges  = self._get_ranges(cfg = cfg)
        data    = self._get_subdataset(cfg = cfg)
        if ranges is None:
            l_nll = [self._get_nll(data = data, frange = None)]
        else:
            l_nll = [ self._get_nll(data = data, frange = frange) for frange in ranges ]

        nnll    = len(l_nll)
        log.info(f'Using {nnll} likelihoods')
        nll     = sum(l_nll[1:], l_nll[0])

        if cfg.constraints is None:
            log.debug('Not using any constraint')
            return nll

        log.info('Adding constraints')
        zconstraints= [ const.zfit_cons(holder = nll) for const in cfg.constraints ]
        nll         = nll.create_new(constraints = zconstraints)

        return nll
    #------------------------------
    def _plot_fit(self, nll : Loss) -> None:
        '''
        Parameters
        ---------------
        nll: Negative log likelihood with model and data from fit
        '''
        data = nll.data[0]
        pdf  = nll.model[0]

        cfg  = ZFitPlotterConf(nbins = 50)
        obj  = ZFitPlotter(data=data, model=pdf, result=None)
        obj.plot(cfg)
        plt.show()
    #------------------------------
    def _update_par_bounds(
        self,
        res    : FitResult,
        nsigma : float,
        yields : list[str]) -> None:

        s_shape_par = self._pdf.get_params(is_yield=False, floating=True)
        d_shp_par   = { par.name : par for par in s_shape_par if par.name not in yields}

        log.info(60 * '-')
        log.info(f'{"Parameter":<20}{"Low bound":<20}{"High bound":<20}')
        log.info(60 * '-')
        for shape_par_name, shape_par in d_shp_par.items():
            val, err        = res[shape_par_name]
            shape_par.lower = val - nsigma * err
            shape_par.upper = val + nsigma * err

            log.info(f'{shape_par_name:<20}{val - err:<20.3e}{val + err:<20.3e}')
    #------------------------------
    @property
    def nll(self) -> Loss:
        '''
        Negative log likelihood, raises if NLL missing
        '''
        if self._nll is None:
            raise ValueError('Missing NLL, fit was not ran?')

        return self._nll
    #------------------------------
    def fit(
        self,
        cfg : FitConf | None = None) -> FitResult:
        '''
        Runs the fit using the configuration specified by the cfg dictionary
        Parameters
        ----------------------
        cfg : Minimization configuration

        Returns
        ----------------------
        Fit result object
        '''
        cfg = FitConf.default() if cfg is None else cfg
        nll = self._get_full_nll(cfg = cfg)

        if cfg.strategy is None:
            log.info('Not using any strategy, simple fit')

            res       = minimizers.minimize(nll, cfg)
            self._nll = nll

            return res

        if isinstance(cfg.strategy, Retries):
            log.info('Using retry strategy')

            obj = AnealingMinimizer(cfg = cfg)
            res = obj.get_result(loss = nll)
            self._set_pdf_pars(res)

            return res

        raise ValueError(f'Unsupported fitting strategy: {cfg.strategy}')
#------------------------------
