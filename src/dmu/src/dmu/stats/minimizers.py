'''
Module containing derived classes from ZFit minimizer
'''
import math
import numpy
import tempfile
import matplotlib.pyplot as plt

from typing                        import Final
from pathlib                       import Path
from multiprocessing               import get_context
from zfit                          import dill
from zfit.loss                     import ExtendedUnbinnedNLL
from zfit.loss                     import UnbinnedNLL
from zfit.result                   import FitResult as zres
from zfit.pdf                      import BasePDF           as zpdf
from zfit.minimizers.errors        import WeightCorr
from zfit.minimizers.strategy      import FailMinimizeNaN

from dmu                           import LogStore
from dmu.logging                   import messages  as mes
from dmu.logging                   import LogLevels

from .gof_calculator import GofCalculator
from .fit_result     import FitResult, GoodnessOfFit
from .utilities      import print_pdf
from .fit_conf       import Context, Retries, FitConf
from .imports        import zfit
from .exceptions     import MinimizerFailError, ErrorFailError
from .               import utilities as sut

log = LogStore.add_logger('dmu:stats:minimizers')

type zlos = ExtendedUnbinnedNLL | UnbinnedNLL
type zpar = zfit.param.Parameter
type zmin = zfit.minimize.Minuit

# Should always be these values
_HIDDEN_TF_LINES          : Final[list[str]] = [
    'Loaded cuDNN version',
    'abnormal_detected_host @',
    'Skipping loop optimization for Merge',
    'Creating GpuSolver handles for stream',
    'Loaded cuDNN version',
    'All log messages before absl::InitializeLog()']

_NDOF         : Final[int] = 10             # Numbe of degrees of freedom for goodness of fit calculation
_ERROR_METHOD : Final[str] = 'minuit_hesse' # Method used to calculate errors
# ------------------------
class AnealingMinimizer:
    '''
    Class meant to minimizer zfit likelihoods by using multiple retries,
    each retry is preceeded by the randomization of the fitting parameters
    '''
    # ------------------------
    def __init__(self, cfg : FitConf | None = None):
        '''
        Parameters
        ----------------
        cfg: Object storing configuration
        '''
        if cfg is None:
            stt = Retries.default()
            cfg = FitConf.default()
            cfg = cfg.model_copy(update = {'strategy' : stt})

        if not isinstance(cfg.strategy, Retries):
            raise ValueError(f'Using AnealingMinimizer with strategy: {cfg.strategy}')

        self._strategy   = cfg.strategy
        self._cfg        = cfg
        self._target_gof = GoodnessOfFit(
            pval = self._strategy.pvalue,
            ndof = _NDOF)

        self._l_bad_fit_res : list[zres] = []

        min_conf  = cfg.minimization.model_dump()
        self._min = zfit.minimize.Minuit(**min_conf)
    # ------------------------
    def _is_good_fit(self, res : zres) -> bool:
        good_fit = True

        if not res.valid:
            log.debug('Skipping invalid fit')
            good_fit = False

        if res.status != 0:
            log.debug('Skipping fit with bad status')
            good_fit = False

        if not res.converged:
            log.debug('Skipping non-converging fit')
            good_fit = False

        if not good_fit:
            self._l_bad_fit_res.append(res)

        return good_fit
    # ------------------------
    def _randomize_parameters(self, nll : zlos):
        '''
        Will move floating parameters of PDF according
        to uniform PDF
        '''

        log.debug('Randomizing parameters')
        l_model = nll.model
        if len(l_model) != 1:
            raise ValueError('Not found and and only one model')

        model = l_model[0]
        s_par = model.get_params(floating=True)
        for par in s_par:
            ival = par.value().numpy()

            lower, upper = self._param_bounds(par = par)
            fval = numpy.random.uniform(lower, upper)
            par.set_value(fval)
            log.debug(f'{par.name:<40}{ival:<15.3f}{"->":<10}{fval:<15.3f}{"in":<5}{par.lower:<15.3e}{par.upper:<15.3e}')
    # ----------------------
    def _param_bounds(
        self,
        par            : zpar,
        must_be_finite : bool = True) -> tuple[float,float]:
        '''
        Parameters
        -------------
        par: Zfit parameter
        must_be_finite: If true, will raise an exception if a bound is None.

        Returns
        -------------
        Tuple with bounds
        '''
        lower : float = math.inf if par.lower is None else float(par.lower.numpy())
        upper : float = math.inf if par.upper is None else float(par.upper.numpy())

        fail_lower = lower == math.inf and must_be_finite
        fail_upper = upper == math.inf and must_be_finite

        if fail_upper or fail_lower:
            raise ValueError(f'Either bound is not finite for {par.name}: [{lower}, {upper}]')

        return lower, upper
    # ------------------------
    def _pick_best_fit(self, d_chi2_res : dict) -> zres | None:
        nres = len(d_chi2_res)
        if nres == 0:
            log.error('No fits found')
            return None

        l_chi2_res= list(d_chi2_res.items())
        l_chi2_res.sort()
        chi2, res = l_chi2_res[0]

        log.warning(f'Picking out best fit from {nres} fits with chi2: {chi2:.3f}')

        return res
    #------------------------------
    def _set_pdf_pars(self, res : zres, pdf : zpdf) -> None:
        '''
        Will set the PDF floating parameter values as the result instance
        '''
        l_par_flt = list(pdf.get_params(floating= True))
        l_par_fix = list(pdf.get_params(floating=False))
        l_par     = l_par_flt + l_par_fix

        d_val = { par.name : dc['value'] for par, dc in res.params.items()}

        log.debug('Setting PDF parameters to best result')
        for par in l_par:
            if par.name not in d_val:
                par_val = par.value().numpy()
                log.debug(f'Skipping {par.name} = {par_val:.3e}')
                continue

            val = d_val[par.name]
            log.debug(f'{"":<4}{par.name:<20}{"->":<10}{val:<20.3e}')
            par.set_value(val)
    # ------------------------
    def _pdf_from_nll(self, nll : zlos) -> zpdf:
        l_model = nll.model
        if len(l_model) != 1:
            raise ValueError('Cannot extract one and only one PDF from NLL')

        return l_model[0]
    # ------------------------
    def _print_failed_fit_diagnostics(self, nll : zlos) -> None:
        for res in self._l_bad_fit_res:
            print(res)

        arr_mass = nll.data[0].numpy()

        plt.hist(arr_mass, bins=60)
        plt.show()
    # ------------------------
    def get_result(self, loss : zlos) -> FitResult:
        '''
        Parameters
        -----------------
        loss: NLL that will be minimized

        Returns
        -----------------
        Object holding fit result
        '''
        results : list[FitResult] = []
        log.info(30 * '-')
        log.info(f'{"Try":<5}{"Chi2/Status":>25}')
        log.info(30 * '-')
        for i_try in range(1, self._strategy.ntries + 1):
            if i_try > 1:
                self._randomize_parameters(loss)

            try:
                obj = self._min.minimize(loss)
                res = _calculate_errors(
                    res = obj,
                    cfg = self._cfg,
                    gof = GoodnessOfFit.none(),
                    nll = loss)
            except (ErrorFailError, FailMinimizeNaN, ValueError, RuntimeError, MinimizerFailError):
                for pdf in loss.model:
                    print_pdf(pdf, level = LogLevels.debug)

                log.info(f'{i_try:02}/{self._strategy.ntries:02}{"Failed minimization":>25}')
                continue

            gcl = GofCalculator(nll = loss)
            gof = gcl.get_gof()

            if not res.valid:
                log.info(f'{i_try:02}/{self._strategy.ntries:02}{"Invalid minimum":>25}')
                continue

            if res.cov_status != 0:
                log.info(f'{i_try:02}/{self._strategy.ntries:02}{"Invalid covariance":>25}')
                continue

            log.info(f'{i_try:02}/{self._strategy.ntries:02}{gof.chi2:>25.3f}')
            if gof < self._target_gof:
                results.append(res)
                continue

            if gof > self._target_gof:
                log.info('Found fit satisfying target GOF:')
                log.info(gof)
                return res

        if not results:
            path = sut.save_nll(loss = loss)
            raise ValueError(f'No valid results found, NLL saved to: {path}')

        results     = sorted(results)
        best_result = results[-1]

        pdf  = self._pdf_from_nll(loss)
        pars = pdf.get_params()
        best_result.set_pars(pars = pars)

        return results[-1]
# ------------------------
class ContextMinimizer:
    '''
    Class meant to run minimization in a separate process
    This is needed to deal with the memory leak described here:

    https://github.com/zfit/zfit/issues/665

    And could be removed once issue is fixed
    '''
    # ----------------------
    def __init__(self, minimizer : zmin):
        '''
        Parameters
        ---------------
        min: Minimizer
        '''
        self._ctx = get_context(method = 'spawn')
        self._min = dill.dumps(minimizer)
    # ----------------------
    @staticmethod
    def _proc_minimize(
        onll: bytes,
        omin: bytes,
        path: Path):
        '''
        This method is meant to run the minimization in a separate python
        process. Thus when the process ends, memory is released. It is meant
        to prevent memory leak in zfit minimization step

        Parameters
        ----------------
        onll: Bytes representation of likelihood
        omin: Bytes representation of minimizer
        path: Path where the result object will be saved
        '''
        from zfit import dill             # noqa: PLC0415
        from .fit_result import FitResult # noqa: PLC0415

        nll              = dill.loads(onll)
        minimizer : zmin = dill.loads(omin)

        res = minimizer.minimize(loss = nll)
        res.hesse(name = 'minuit_hesse')

        frs = FitResult.from_zfit(res = res)
        frs.to_json(path= path)
    # ----------------------
    def minimize(self, loss : zlos) -> FitResult:
        '''
        Parameters
        -------------
        loss: zfit Negative log likelihood

        Returns
        -------------
        FitResult object
        '''
        nll_byt = dill.dumps(loss)

        with tempfile.NamedTemporaryFile(mode='w+b', delete=True) as temp:
            path = Path(temp.name)

            args = nll_byt, self._min, path
            proc = self._ctx.Process(target = self._proc_minimize, args = args)
            proc.start()
            proc.join()

            frs = FitResult.from_json(path = path)

        return frs
# ------------------------
def _get_weight_corr(nll : zlos) -> WeightCorr:
    has_weights = False
    for data in nll.data:
        if data.weights is None:
            continue

        weights = data.weights.numpy()
        if not numpy.all(weights == 1):
            has_weights = True

    if has_weights:
        return WeightCorr('asymptotic')

    return WeightCorr(False)
# ------------------------
def _calculate_errors(
    res : zres,
    cfg : FitConf,
    gof : GoodnessOfFit,
    nll : zlos) -> FitResult:
    '''
    Parameters
    -------------
    res: Result of fit, before error calculation
    cfg: Configuration for fit
    gof: Object holding goodness of fit from minimization stage
    nll: Likelihood, will save it if failure

    Returns
    -------------
    Fit result with errors added
    '''
    if not cfg.do_errors:
        log.warning('Not calculating fit errors')
        return FitResult.from_zfit(
            res          = res,
            gof          = gof,
            no_errors_ok = not cfg.do_errors)

    log.debug('Calculating errors')

    weight_corr = _get_weight_corr(nll = nll)
    try:
        res.hesse(
            weightcorr = weight_corr,
            name       = _ERROR_METHOD,
            method     = _ERROR_METHOD)

        cov = res.covariance(method = _ERROR_METHOD, weightcorr = weight_corr)

        setattr(res, 'cov', cov) # noqa: B010
    except ValueError as exc:
        log.info('Failed error calculation')
        raise ErrorFailError('Failed calculating error') from exc

    return FitResult.from_zfit(
        res          = res,
        gof          = gof,
        no_errors_ok = not cfg.do_errors)
# ------------------------
def minimize(
    nll : zlos,
    cfg : FitConf | None = None)-> FitResult:
    '''
    Parameters
    --------------
    nll : Negative log likelihood
    cfg : Fit configuration object

    Returns
    --------------
    Object storing fit results

    Raises
    --------------
    RuntimeError: If the errors could not be calculated
    '''
    if cfg is None:
        cfg = FitConf.default()

    mnm = zfit.minimize.Minuit(**cfg.minimization.model_dump())

    if isinstance(cfg.strategy, Context):
        log.info('Using context minimizer')
        mnm = ContextMinimizer(minimizer = mnm)

    with mes.filter_stderr(banned_substrings=_HIDDEN_TF_LINES):
        try:
            obj = mnm.minimize(loss = nll)
        except (FailMinimizeNaN, RuntimeError) as exc:
            path = sut.save_nll(loss = nll)
            log.error(f'Saved NLL in: {path}')
            raise MinimizerFailError('Minimization failed') from exc

    if not obj.valid:
        log.error(obj)
        path = sut.save_nll(loss = nll)
        raise MinimizerFailError(f'Fit result invalid, likelihood saved to: {path}')

    if cfg.run_gof:
        gcl = GofCalculator(nll = nll)
        gof = gcl.get_gof()
    else:
        gof = GoodnessOfFit.none()

    if isinstance(obj, zres):
        res = _calculate_errors(
            res = obj,
            cfg = cfg,
            gof = gof,
            nll = nll)
    else:
        res = obj

    if res.cov_status != 0:
        path = sut.save_nll(loss = nll)
        log.warning(f'Found bad covariance, saving NLL to: {path}')

    if res.valid:
        return res

    if gof:
        log.debug('Found bad fit')
        log.debug(f'{gof.chi2:<10.3f}{gof.pval:<10.3e}{res.status:<10}')
    else:
        log.debug('Found bad fit, no GOF (turned off)')

    if log.getEffectiveLevel() < LogLevels.info:
        log.info(res)
        pdf = nll.model[0] # This class is not meant for simultaneous fits
                         # There should only be one PDF
        print_pdf(pdf)

    return res
# ------------------------
