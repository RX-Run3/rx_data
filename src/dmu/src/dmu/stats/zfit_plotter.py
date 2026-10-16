'''
Module containing plot class, used to plot fits
'''

import math
import hist
import mplhep
import pandas                as pd
import numpy                 as np
import matplotlib.pyplot     as plt
import matplotlib.colors     as mcolors

from hist                    import Hist, BaseHist
from mplhep.error_estimation import poisson_interval
from typing                  import Final
from matplotlib.axes         import Axes
from zfit.pdf                import BasePDF    as zpdf
from zfit.data               import Data       as zdat
from zfit.result             import FitResult  as zres
from dmu                     import LogStore

from .zfit_plotter_conf     import ZFitPlotterConf
from .fit_result            import FitResult
from .imports               import zfit, tensorflow as tf

param      = zfit.param
Npaflt     = np.ndarray[tuple[int], np.dtype[np.float64]]
type Range = tuple[float,float]
type zpar  = zfit.param.Parameter

log = LogStore.add_logger('dmu:zfit_plotter')
plt.style.use(mplhep.style.LHCb2)

_Y_MIN_LOG      : Final[float] = 0.1
'''Minimum in y-axis when plotting in log scale'''
_Y_MAX_LOG_SCALE: Final[float] = 10000
'''Factory by which to multiply maximum of histogram when plotting in log scale'''

_NORMAL_BINNING : Final[int  ] = 100
_FINE_BINNING   : Final[int  ] = 200
_MAX_PULL       : Final[int  ] = 5    # If fit ull is beyond this, will print info message
_NXPOINTS       : Final[int  ] = 2000 
'''Number of points to scan PDF for both plotting or calculating normalization'''
_ALPHA          : Final[float] =  0.8 # Transparency of PDF plots when stacking
_MIN_LIMITS     : Final[int]   = 2    # Need at least upper and lower limit in observable

#-------------------------------------------------------
def _range_from_obs(obs : zfit.Space) -> tuple[float,float]:
    '''
    Takes zfit observable, returns tuple with two floats, representing range
    '''
    if not isinstance(obs.limits, tuple):
        raise ValueError(f'Cannot retrieve name for: {obs}')

    if len(obs.limits) != _MIN_LIMITS:
        raise ValueError(f'Observable has more than one range: {obs.limits}')

    minx, maxx = obs.limits

    if not isinstance(minx, np.ndarray):
        raise ValueError(f'Minx is not an array but: {minx}')

    if not isinstance(maxx, np.ndarray):
        raise ValueError(f'Minx is not an array but: {maxx}')

    lower : float = minx[0][0]
    upper : float = maxx[0][0]

    return lower, upper 
#-------------------------------------------------------
def _name_from_obs(obs : zfit.Space) -> str:
    '''
    Takes zfit observable, returns its name
    It is assumed this is a 1D observable
    '''
    if not isinstance(obs.obs, tuple):
        raise ValueError(f'Cannot retrieve name for: {obs}')

    if len(obs.obs) != 1:
        raise ValueError(f'Observable is not 1D: {obs.obs}')

    return obs.obs[0]
#----------------------------------------
class EmptyDataSet(Exception):
    '''
    Meant to be used when there is no data to be plotted
    '''
    ...
#----------------------------------------
class ZFitPlotter:
    '''
    Class used to plot fits done with zfit
    '''
    #----------------------------------------
    def __init__(
        self,
        data   : zdat | np.ndarray | pd.Series | pd.DataFrame,
        model  : zpdf,
        weights: np.ndarray| None = None,
        result : zres | None      = None):
        '''
        Parameters
        ------------------
        data   : The data you are fit on
        model  : The final total fit model
        weights: 1D numpy array of weights
        result : Zfit fit result object
        '''
        if not isinstance(model.space, zfit.Space):
            raise ValueError('No observable found in PDF')

        self.obs               = model.space
        self.norm              = model.space if not isinstance(model.norm, zfit.Space) else model.norm
        self._obs_name         = _name_from_obs(obs = self.obs)

        self.data              = self._data_to_zdata(data, weights)
        self.total_model       = model
        self.data_np           = self.data.numpy().flatten()

        self.data_weight_np    = np.ones_like(self.data_np) if self.data.weights is None else self.data.weights.numpy().flatten()
        self._result           = result

        self.errors : list[tuple[float,float]] = []
        self.axs                : tuple[Axes,...]
        self._data_hist  : BaseHist | None            = None
        self.cfg                : ZFitPlotterConf             = ZFitPlotterConf()

        self._l_def_col = list(mcolors.TABLEAU_COLORS.keys())
    #----------------------------------------
    def _data_to_zdata(
        self,
        data    : np.ndarray | zfit.Data | pd.Series | pd.DataFrame,
        weights : np.ndarray | None) -> zfit.Data:
        '''
        Parameters
        -----------------
        data   : Original data
        weights: Weights or None for unweighted case

        Returns
        -----------------
        zfit data object
        '''
        if   isinstance(data, zfit.Data):
            return data

        if isinstance(data, np.ndarray):
            out_data = zfit.Data.from_numpy (obs=self.obs, array=data           , weights=weights)
        elif isinstance(data, pd.Series):
            out_data = zfit.Data.from_pandas(obs=self.obs, df=pd.DataFrame(data), weights=weights)
        elif isinstance(data, pd.DataFrame):
            out_data = zfit.Data.from_pandas(obs=self.obs, df=data              , weights=weights)
        else:
            raise ValueError(f'Passed data is of usupported type {type(data)}')

        if not isinstance(out_data, zfit.Data):
            raise ValueError('Cannot get zfit data')

        return out_data
    #----------------------------------------
    def _get_marker_size(self) -> float:
        '''
        Parameters
        -----------------
        nbins: Number of bins used for data historam and pulls

        Returns
        -----------------
        Size of marker
        '''
        if self.nbins <= _NORMAL_BINNING:
            return 1.

        if self.nbins <= _FINE_BINNING:
            return 0.75

        return 0.5
    #----------------------------------------
    def _get_errors(
        self,
        l_range: list[Range] | None = None) -> list[Range]:
        '''
        Parameters
        ---------------------
        l_range: List of ranges where data should be picked, if None, will pick full range

        Returns
        ---------------------
        list of errors associated to histogram filled with data
        '''
        lower, upper = self.plot_range
        dat, wgt     = self._get_range_data(l_range=l_range, blind=False)
        data_hist    = hist.Hist.new.Regular(
            self.nbins,
            lower,
            upper,
            name       =self._obs_name,
            underflow  =False,
            overflow   =False)

        data_hist = data_hist.Weight()
        data_hist.fill(dat, weight=wgt)

        values   = data_hist.values()
        variance = data_hist.variances()

        errors : tuple[Npaflt, Npaflt] = poisson_interval(values, variance)
        low, up                        = errors

        l_error  = list(zip(values - low, up - values, strict = True))

        return l_error
    #----------------------------------------
    def _get_range_data(
        self,
        l_range : list[Range] | None,
        blind   : bool = True) -> tuple[Npaflt, Npaflt]:
        '''
        Parameters
        -----------------
        l_range: List of ranges, i.e. tuples of bounds
        blind  : If true (default) will blind the range specified, i.e. will exclude it

        Returns
        -----------------
        Tuple with two numpy arrays defined in those ranges, with the observable and the weights.
        '''
        sdat  = self.data_np
        swgt  = self.data_weight_np
        dmat  = np.array([sdat, swgt]).T

        if blind and self.cfg.blind is not None:
            log.debug(f'Blinding data with: {self.cfg.blind}')
            _, min_val, max_val = self.cfg.blind
            mask                = (dmat.T[0] < min_val) | (dmat.T[0] > max_val)
            dmat                = dmat[mask]

        if l_range is None:
            dat : Npaflt = dmat.T[0]
            wgt : Npaflt = dmat.T[1]

            self._check_data(dat=dat, wgt=wgt)

            return dat, wgt

        l_dat = []
        l_wgt = []
        for lo, hi in l_range:
            mask   : np.ndarray = (dmat.T[0] > lo) & (dmat.T[0] < hi)
            dmat_f : np.ndarray = dmat[mask]

            [dat, wgt] = dmat_f.T

            l_dat.append(dat)
            l_wgt.append(wgt)

        dat_f = np.concatenate(l_dat)
        wgt_f = np.concatenate(l_wgt)

        self._check_data(dat=dat_f, wgt=wgt_f)

        return dat_f, wgt_f
    #----------------------------------------
    def _check_data(
        self,
        dat : Npaflt,
        wgt : Npaflt) -> None:
        '''
        Checks for empty data, etc

        Parameters
        ------------
        Numpy arrays with data and weights
        '''
        if dat.shape != wgt.shape:
            raise ValueError(f'Shapes or data and weights differ: {dat.shape}/{wgt.shape}')

        if len(dat) == 0:
            raise EmptyDataSet('Dataset is empty')
    #----------------------------------------
    def _plot_data(
        self,
        ax      : Axes,
        l_range : None | list[Range] = None) -> BaseHist:

        dat, wgt     = self._get_range_data(l_range, blind=True)
        lower, upper = self.plot_range

        builder   = hist.Hist.new.Regular(self.nbins, lower, upper, name=self._obs_name, underflow=False, overflow=False)
        data_hist = builder.Weight()
        data_hist.fill(dat, weight=wgt)

        mplhep.histplot(
            data_hist,
            yerr       = True,
            markersize = self._get_marker_size(),
            color      = 'black',
            histtype   = 'errorbar',
            label      = self.cfg.d_leg.get('Data', 'Data'),
            ax         = ax)

        self._data_hist = data_hist

        return data_hist
    #----------------------------------------
    def _pull_hist(
        self,
        pdf_hist   : Hist,
        l_range    : None | list[Range] = None) -> tuple[Hist, list[Range]]:
        lower, upper        = self.plot_range
        pdf_values : Npaflt = pdf_hist.values()
        dat, wgt  = self._get_range_data(l_range, blind=False)
        hist_bldr = hist.Hist.new.Regular(self.nbins, lower, upper, name=self._obs_name, underflow=False, overflow=False)
        data_hist = hist_bldr.Weight()
        data_hist.fill(dat, weight=wgt)

        data_values : Npaflt = data_hist.values()

        scale       = sum(data_values) / sum(pdf_values)
        pdf_val_scl = [ value * scale for value in pdf_values ]

        pulls       : list[float] = []
        pull_errors : list[Range] = []
        for (low, up), pdf_val, dat_val in zip(self.errors, pdf_val_scl, data_values, strict = True):
            res = float(dat_val - pdf_val)
            err = low if res > 0 else up
            pul = res / err

            # If the data is weighted
            # and the data does not exist
            # The pulls will have an error of zero => pull is inf
            # Ignore these cases
            if math.isinf(pul):
                pass
            elif abs(pul) > _MAX_PULL:
                log.info(f'Pull: {pul:.2f}=({dat_val:.2f}-{pdf_val:.2f})/{err:.2f}')
            else:
                log.debug(f'Pull: {pul:.2f}=({dat_val:.2f}-{pdf_val:.2f})/{err:.2f}')

            pulls.append(pul)

            errors = low / err, up  / err
            pull_errors.append(errors)

        hst            = hist.new.Reg(self.nbins, lower, upper, name="pulls").Double()
        pull_hist      = hist.Hist(hst)
        pull_hist[...] = pulls

        return pull_hist, pull_errors
    #----------------------------------------
    def _plot_pulls(
        self,
        *,
        ax      : Axes,
        l_range : list[Range] | None) -> None:

        obs_name     = self._obs_name
        lower, upper = self.plot_range
        binning      = zfit.binned.RegularBinning(bins=self.nbins, start=lower, stop=upper, name=obs_name)
        binned_obs   = zfit.Space(obs_name, binning=binning)
        binned_pdf   = zfit.pdf.BinnedFromUnbinnedPDF(self.total_model, binned_obs)
        pdf_hist     = binned_pdf.to_hist()

        pull_hist, pull_errors = self._pull_hist(pdf_hist = pdf_hist, l_range = l_range)

        mplhep.histplot(
            H          = pull_hist,
            color      = "black",
            histtype   = "errorbar",
            markersize = self._get_marker_size(),
            yerr       = np.array(pull_errors).T,
            ax         = ax)
    #----------------------------------------
    def _get_zfit_gof(self) -> str | None:
        '''
        Returns goodness of fit string
        '''
        if not self._result or not hasattr(self._result, 'gof'):
            return None

        chi2, ndof, pval = getattr(self._result, 'gof') # noqa: B009
        rchi2 : float    = chi2 / ndof

        return (
            fr'$\chi^2$/NdoF={chi2:.2f}/{ndof}={rchi2:.2f}'
            f'\np={pval:.3f}')
    #----------------------------------------
    def _get_text(self, ext_text : str | None) -> str | None:
        '''
        Returns text used in plot, None if no text can be found
        '''
        gof_text = self._get_zfit_gof()

        if ext_text is     None and gof_text is     None:
            return None

        if ext_text is not None and gof_text is     None:
            return ext_text

        if ext_text is     None and gof_text is not None:
            return gof_text

        return f'{ext_text}\n{gof_text}'
    #----------------------------------------
    def _get_pars(self) -> dict[str, list[float]]:
        '''
        Will return a dictionary with:
        ```
        par_name -> [value, error]
        ```

        if error is not available, will assign zeros
        '''
        if self._result is not None:
            res   = FitResult.from_zfit(
                res          = self._result,
                no_errors_ok = True)
            pars  = res.parameters
            d_par = { par.name : [par.value, par.error] for par in pars }
        else:
            s_par = self.total_model.get_params()
            d_par = {par.name : [float(par.value()), 0] for par in s_par }

        return d_par
    #----------------------------------------
    def _add_pars_box(self, add_pars : list[str] | str) -> None:
        '''
        Will add parameter values to box to the right of fit plot

        Parameters:
        ------------------
        add_pars (list|str): List of names of parameters to be added or string with value 'all' to add all fit parameters.
        '''
        d_par = self._get_pars()

        line = ''
        for name, [val, err] in d_par.items():
            if add_pars != 'all' and name not in add_pars:
                continue

            line += f'{name:<20}{val:>10.3e}{"+/-":>5}{err:>10.3e}\n'

        plt.text(0.65, 0.75, line, fontsize=12, transform=plt.gcf().transFigure)
    #----------------------------------------
    def _get_axis(self) -> tuple[Axes,...]:
        '''
        Returns
        ----------------
        Tuple with axes for main fit and pull
        '''
        if self.cfg.axs:
            return self.cfg.axs

        if self.cfg.skip_pulls:
            _, ax = plt.subplots(1)
            return ax,

        if self.cfg.add_pars is None:
            fig       = plt.figure(figsize = self.cfg.figsize)
            gs        = fig.add_gridspec(nrows=2, ncols=1, hspace=0.1, height_ratios=[4, 1])
            axs       = gs.subplots(sharex=True)
            taxs      = tuple(axs.flat) # type: ignore

            return taxs

        fig = plt.figure(figsize=self.cfg.figsize)
        ax1 = plt.subplot2grid((4,40),(0, 0), rowspan=3, colspan=25)
        ax2 = plt.subplot2grid((4,40),(3, 0), rowspan=1, colspan=25)
        plt.subplots_adjust(hspace=0.2)

        self._add_pars_box(self.cfg.add_pars)

        return ax1, ax2
    #----------------------------------------
    def _get_component_yield(
        self,
        *,
        par : param.Parameter,
        name: str) -> float:
        '''
        Returns yield in normalization range of model's component PDF
        '''
        frac : float = float(par.value().numpy())
        yld  : float = frac * self.norm_yield

        log.verbose(f'Found yield {yld:,.5g} for component {name}')

        return yld
    #----------------------------------------
    def _plot_model_components(self, *, stacked : bool) -> None:
        if not isinstance(self.total_model, zfit.pdf.SumPDF):
            return

        blind_name = None if self.cfg.blind is None else self.cfg.blind[0]

        y   : None | Npaflt            = None
        l_y : list[tuple[Npaflt, str]] = []
        was_blinded                    = False
        for model, frac in zip(self.total_model.pdfs, self.total_model.params.values(), strict = True):
            if model.name == blind_name:
                was_blinded = True
                log.debug(f'Skipping blinded PDF: {blind_name}')
                continue

            models = self._get_components(model = model, frac = frac)
            l_y   += self._scan_subcomponents(
                y       = y,
                stacked = stacked,
                l_model = models)

            nsubcomp = len(l_y)
            log.debug(f'Plotting {nsubcomp} subcomponents for {model.name}')

            y, _  = l_y[-1]

        l_y.reverse() # puts next plot BEHIND last plot
        ax  = self.axs[0]
        xs  = self._get_xcoor(rng = self.plot_range)
        for ys, name in l_y:
            log.debug(f'Plotting {name}')
            if stacked:
                ax.fill_between(xs, ys * self.hist_area, alpha=_ALPHA, label=self.cfg.d_leg.get(name, name), color=self._get_color(name))
            else:
                ax.plot(xs, ys * self.hist_area, ':',                  label=self.cfg.d_leg.get(name, name), color=self.cfg.d_col.get(name))

        if (blind_name is not None) and (was_blinded is False):
            for model in self.total_model.pdfs:
                log.info(model.name)

            raise ValueError(f'Blinding was requested, but PDF {blind_name} was not found')
    #----------------------------------------
    def _scan_subcomponents(
        self,
        *,
        y       : Npaflt | None,
        stacked : bool,
        l_model : list[tuple[float,zpdf]]) -> list[tuple[Npaflt, str]]:
        '''
        Will split model component into sub components, if needed.

        Returns
        ---------------
        List of tuples with:

        - Array of normalized to data y values of PDF
        - Component name
        '''
        l_y : list[tuple[Npaflt, str]] = []

        xs = self._get_xcoor(rng = self.plot_range)
        for frc, model in l_model:
            ys = self._evaluate_pdf(pdf = model, xs = xs) * frc

            if stacked:
                y = ys if y is None else y + ys
            else:
                y = ys 

            l_y.append((y, model.name))

        return l_y
    #----------------------------------------
    def _get_components(self, model : zpdf, frac : zpar) -> list[tuple[float,zpdf]]:
        '''
        Parameters
        ----------------
        model: PDF meant to be split into subcomponents
        frac : Fraction of this PDF in full model

        Returns
        ----------------
        List of tuples where:

        - Fraction of this component WRT full model
        - Component
        '''
        outer_frac = self._float_from_par(frac)
        split_model= model.name in self.cfg.plot_components

        if split_model and isinstance(model, zfit.pdf.SumPDF):
            log.debug(f'Plotting subcomponents for {model.name}')
            zipped = zip(model.pdfs, model.params.values(), strict = True)
            return [ (outer_frac * self._float_from_par(frc), pdf) for pdf, frc in zipped ]

        if split_model and not isinstance(model, zfit.pdf.SumPDF):
            log.warning(f'Cannot plot {model.name} as separate components, despite it was requested')
        else:
            log.debug(f'Not plotting subcomponents for {model.name}')

        return [ (outer_frac, model) ]
    #----------------------------------------
    def _float_from_par(self, par : zpar) -> float:
        '''
        Numerical value of parameter
        '''
        return float(par.value().numpy())
    #----------------------------------------
    def _get_color(self, name : str) -> str:
        '''
        Returns name of color associated to PDF component
        OR default color
        '''
        if name in self.cfg.d_col:
            return self.cfg.d_col[name]

        col = self._l_def_col[0]
        del self._l_def_col[0]

        return col
    #----------------------------------------
    def _print_data(self) -> None:
        log.info(f'Data shape  : {self.data_np.shape}')
        log.info(f'Weights shape: {self.data_weight_np.shape}')

        nnans = np.sum(np.isnan(self.data_np))
        log.info(f'NaNs: {nnans}')

        # This function will run before program raises
        # One should be able to drop any plot
        plt.close('all')
        plt.hist(self.data_np, weights=self.data_weight_np)
        plt.show()
    #----------------------------------------
    def _evaluate_pdf(
        self,
        pdf : zpdf,
        xs  : Npaflt) -> Npaflt:
        '''
        Parameters
        -----------------
        xs : Coordinates in x axis in the plotting range
        pdf: PDF to scan

        Returns 
        -----------------
        array of y coordinates for array of x corrdinates and a given PDF
        in the plotting range
        '''
        try:
            tensor : tf.Tensor = pdf.pdf(x = xs)
        except Exception as exc:
            log.info(f'X values: {xs}')
            self._print_data()
            raise ValueError('Cannot evaluate PDF') from exc

        rng= self.plot_range
        ys = tensor.numpy()
        ys = ys / self._integrate(pdf = pdf, rng = rng) 

        bin_area = ys * self.scan_width
        area = float(bin_area.sum())
        if not math.isclose(area, 1, abs_tol=0.01):
            raise ValueError(f'{pdf.name} not normalized to unity but {area:.3f} in {rng}')

        return ys
    #----------------------------------------
    def _integrate(self, pdf : zpdf, rng : Range) -> float:
        '''
        Parameters
        ----------------
        pdf: zfit PDF
        rng: Tuple with range where to integrate

        Returns
        ----------------
        Integral as a float
        '''
        tensor  = pdf.integrate(limits = rng)
        integral= tensor.numpy()

        return float(integral)
    #----------------------------------------
    def _plot_full_model(
        self,
        ax        : Axes,
        model     : zpdf,
        linestyle : str = '-') -> None:
        '''
        Plots full model when running in stack = False mode
        '''
        if self.cfg.blind is not None:
            log.debug(f'Blinding: {model.name}')
            return

        xs   = self._get_xcoor(rng = self.plot_range)
        ys   = self._evaluate_pdf(pdf = model, xs = xs)
        name = model.name

        ax.plot(
            xs, 
            ys * self.hist_area, 
            ls   = linestyle, 
            label= self.cfg.d_leg.get(name, name), 
            color= self.cfg.d_col.get(name))
    #----------------------------------------
    def _get_labels(self, xlabel : str, ylabel : str, unit : str) -> tuple[str,str]:
        if not xlabel:
            if not self.obs.obs:
                raise ValueError(f'Cannot find observable: {self.obs}')

            obs_name, = self.obs.obs
            xlabel    = f"{obs_name} [{unit}]"

        if not ylabel:
            lower, upper = self.plot_range
            width        = (upper - lower) / self.nbins
            ylabel       = f'Candidates / ({width:.0f} {unit})'

        return xlabel, ylabel
    #----------------------------------------
    def _get_xcoor(self, rng : Range) -> Npaflt:
        '''
        Coordinates in x used to sample PDF
        '''
        lower, upper = rng

        log.debug(f'Scanning models in [{lower:,.5g}, {upper:,.5g}]')

        return np.linspace(lower, upper, _NXPOINTS)
    #----------------------------------------
    def _set_yrange(
        self, 
        data_hist : BaseHist | None, 
        ymax      : float    | None) -> None:
        axis = self.axs[0]
        scale= axis.get_yscale()
        ymin = _Y_MIN_LOG if scale == 'log' else 0

        if data_hist and not ymax and scale == 'log':
            val = _Y_MAX_LOG_SCALE * data_hist.values()
            ymax= np.max(val)

        axis.set_ylim(bottom = ymin, top = ymax)
    #----------------------------------------
    def set_yscale(self, scale : str) -> None:
        self.axs[0].set_yscale(scale)

        self._set_yrange(
            ymax      = self.cfg.ymax,
            data_hist = self._data_hist)
    #----------------------------------------
    @property
    def hist_area(self) -> float:
        '''
        Area of data histogram in plotting range
        '''
        bin_size  = self.plot_width / self.nbins
        hist_area = bin_size * self.plot_yield

        return hist_area 
    #----------------------------------------
    @property
    def norm_yield(self) -> float:
        '''
        Returns yield of data in normalization range
        '''
        data = self.data.with_obs(self.norm)

        if data.has_weights:
            yld : float = data.weights.numpy().sum()
        else:
            yld : float = float(data.nevents.numpy())

        log.debug(f'Found a yield of {yld:,.5g} in range [{self.norm_range}]')

        return yld
    #----------------------------------------
    @property
    def norm_range(self) -> tuple[float,float]:
        '''
        Range where PDF area is meant to be 1
        '''
        return _range_from_obs(obs = self.norm)
    #----------------------------------------
    @property
    def plot_yield(self) -> float:
        '''
        Returns yield of data in plotting range
        '''
        obs_plt = zfit.Space(self._obs_name, limits = self.plot_range) 
        data    = self.data.with_obs(obs_plt)

        if data.has_weights:
            yld : float = data.weights.numpy().sum()
        else:
            yld : float = float(data.nevents.numpy())

        log.debug(f'Found a yield of {yld:,.5g} in range [{self.plot_range}]')

        return yld
    #----------------------------------------
    @property
    def plot_range(self) -> tuple[float,float]:
        '''
        Tuple with lower, upper bound of plots
        '''
        if self.cfg.plot_range is None:
            return _range_from_obs(self.norm)

        return self.cfg.plot_range
    #----------------------------------------
    @property
    def nbins(self) -> int:
        '''
        Number of bins meant for plots
        '''
        return self.cfg.nbins
    #----------------------------------------
    @property
    def plot_width(self) -> float:
        '''
        Width of plotting region 
        '''
        lower, upper = self.plot_range

        return upper - lower
    #----------------------------------------
    @property
    def scan_width(self) -> float:
        '''
        Distance between points when sampling PDFs
        in plotting range
        '''
        return self.plot_width / _NXPOINTS
    #----------------------------------------
    def plot(
        self,
        cfg : ZFitPlotterConf) -> None:
        '''
        Parameters
        ----------------
        cfg : ZFitPlotterConf object storing plotting configuration
        '''
        stacked  = False if not isinstance(self.total_model, zfit.pdf.SumPDF) else cfg.stacked
        self.cfg = cfg.model_copy(update={'stacked': stacked})
        self.axs = self._get_axis()

        try:
            self.errors   = self._get_errors(self.cfg.ranges)
        except EmptyDataSet:
            log.warning('Found empty dataset, skipping plot')
            return

        if not self.cfg.stacked:
            log.debug('Plotting full model, for non-stacked case')
            self._plot_full_model(self.axs[0], self.total_model)

        log.debug('Plotting model components')
        self._plot_model_components(stacked = self.cfg.stacked)

        data_hist : None | BaseHist = None
        if not self.cfg.no_data:
            log.debug('Plotting data')
            data_hist = self._plot_data(self.axs[0], self.cfg.ranges)

        if not self.cfg.skip_pulls and not self.cfg.no_data:
            log.debug('Plotting pulls')
            self._plot_pulls(ax = self.axs[1], l_range = self.cfg.ranges)

        text           = self._get_text(self.cfg.ext_text)
        xlabel, ylabel = self._get_labels(self.cfg.xlabel, self.cfg.ylabel, self.cfg.unit)

        self.axs[0].legend(title=text, fontsize=20, title_fontsize=20, loc=self.cfg.leg_loc)
        self.axs[0].set(xlabel=xlabel, ylabel=ylabel)

        self.axs[0].set_xlim(self.plot_range)

        if self.cfg.yscale is not None:
            self.axs[0].set_yscale(self.cfg.yscale)

        if self.cfg.title is not None:
            self.axs[0].set_title(self.cfg.title)

        self._set_yrange(
            data_hist = data_hist, 
            ymax      = self.cfg.ymax)

        if not self.cfg.skip_pulls:
            self.axs[1].set(xlabel=xlabel, ylabel="pulls")
            self.axs[1].set_xlim(*self.plot_range)

        for ax in self.axs:
            ax.label_outer()

        if self.cfg.pull_styling and not self.cfg.skip_pulls:
            self.axs[1].axhline(y=-3, color='red' , linestyle='-', lw=2)
            self.axs[1].axhline(y= 0, color='gray', linestyle='-', lw=1)
            self.axs[1].axhline(y=+3, color='red' , linestyle='-', lw=2)
            self.axs[1].set_ylim(-5, 5)
    #----------------------------------------
    def run(
        self,
        cfg : ZFitPlotterConf) -> None:
        '''
        Parameters
        ----------------
        cfg: Object storing plotting configuration
        '''
        self.plot(cfg)
#----------------------------------------
