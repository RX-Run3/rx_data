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

from hist                    import Hist
from mplhep.error_estimation import poisson_interval
from typing                  import Final, Self
from pydantic                import BaseModel, Field
from matplotlib.axes         import Axes
from zfit.pdf                import BasePDF    as zpdf
from zfit.data               import Data       as zdat
from zfit.result             import FitResult  as zres
from dmu                     import LogStore
from dmu.generic             import utilities  as gut
from dmu.stats               import utilities  as sut

from .fit_result            import FitResult
from .imports               import zfit, tensorflow as tf

param      = zfit.param
Npaflt     = np.ndarray[tuple[int], np.dtype[np.float64]]
type Range = tuple[float,float]
type zpar  = zfit.param.Parameter

log = LogStore.add_logger('dmu:zfit_plotter')
plt.style.use(mplhep.style.LHCb2)

_Y_MIN_LOG      : Final[float] = 0.01
_NORMAL_BINNING : Final[int  ] = 100
_FINE_BINNING   : Final[int  ] = 200
_MAX_PULL       : Final[int  ] = 5    # If fit ull is beyond this, will print info message
_NXPOINTS       : Final[int  ] = 2000 
'''Number of points to scan PDF for both plotting or calculating normalization'''
_ALPHA          : Final[float] =  0.8 # Transparency of PDF plots when stacking
#----------------------------------------
class EmptyDataSet(Exception):
    '''
    Meant to be used when there is no data to be plotted
    '''
    ...
#----------------------------------------
class ZFitPlotterConf(BaseModel, frozen = True):
    '''
    Class meant to hold configuration for ZFitPlotter
    '''
    nbins           : int
    stacked         : bool
    plot_components : list[str]                 = Field(default_factory=list)
    plot_range      : tuple[float,float] | None = None
    ext_text        : str                       = ''
    title           : str | None                = None
    skip_pulls      : bool                      = False
    d_leg           : dict[str,str]             = Field(default_factory=dict)
    # ---------------------------
    @classmethod
    def default(cls, stacked : bool = True) -> Self:
        '''
        Returns default instance of current class
        '''
        return cls(
            nbins           = 50,
            plot_components = [],
            stacked         = stacked)
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
        self._obs_name         = sut.name_from_obs(obs = self.obs)

        self.data              = self._data_to_zdata(data, weights)
        self.total_model       = model
        self.data_np           = self.data.numpy().flatten()

        self.data_weight_np    = np.ones_like(self.data_np) if self.data.weights is None else self.data.weights.numpy().flatten()
        self._result           = result

        self.errors : list[tuple[float,float]] = []
        self._leg   : dict[str,str]            = {}
        self._col   : dict[str,str]            = {}
        self._l_plot_components : list[str]    = []
        self.axs                : tuple[Axes,...]

        self._nbins      : int    | None              = None
        self._xcoords    : Npaflt | None              = None
        self._plot_range : Range  | None              = None
        self._l_blind : tuple[str,float,float] | None = None
        self._figsize : tuple[int,int]         | None = None
        self._leg_loc : str                    | None = None

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

        if blind and self._l_blind is not None:
            log.debug(f'Blinding data with: {self._l_blind}')
            _, min_val, max_val = self._l_blind
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
        l_range : None | list[Range] = None):

        dat, wgt     = self._get_range_data(l_range, blind=True)
        lower, upper = self.plot_range

        data_hist = hist.Hist.new.Regular(self.nbins, lower, upper, name=self._obs_name, underflow=False, overflow=False)
        data_hist = data_hist.Weight()
        data_hist.fill(dat, weight=wgt)

        mplhep.histplot(
            data_hist,
            yerr       = True,
            markersize = self._get_marker_size(),
            color      = 'black',
            histtype   = 'errorbar',
            label      = self._leg.get('Data', 'Data'),
            ax         = ax)
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
    def _get_axis(
        self,
        add_pars   : list[str] | None | str,
        skip_pulls : bool) -> tuple[Axes,...]:
        '''
        Parameters
        ----------------
        add_pars  : Parameters with values to add in figure, by default None, can be 'all' or list of strings
        skip_pulls: If true will only draw fit

        Returns
        ----------------
        Tuple with axes for main fit and pull
        '''
        if skip_pulls:
            _, (ax) = plt.subplots(1)
            return (ax,)

        if add_pars is None:
            fig       = plt.figure(figsize = self._figsize)
            gs        = fig.add_gridspec(nrows=2, ncols=1, hspace=0.1, height_ratios=[4, 1])
            axs       = gs.subplots(sharex=True)
            taxs      = tuple(axs.flat) # type: ignore

            return taxs

        fig = plt.figure(figsize=self._figsize)
        ax1 = plt.subplot2grid((4,40),(0, 0), rowspan=3, colspan=25)
        ax2 = plt.subplot2grid((4,40),(3, 0), rowspan=1, colspan=25)
        plt.subplots_adjust(hspace=0.2)

        self._add_pars_box(add_pars)

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

        blind_name = None if self._l_blind is None else self._l_blind[0]

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

        l_y.reverse()
        ax  = self.axs[0]
        xs  = self._get_xcoor(rng = self.plot_range)
        for ys, name in l_y:
            log.debug(f'Plotting {name}')
            if stacked:
                ax.fill_between(xs, ys * self.scale, alpha=_ALPHA, label=self._leg.get(name, name), color=self._get_color(name))
            else:
                ax.plot(xs, ys * self.scale, ':',                  label=self._leg.get(name, name), color=self._col.get(name))

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
        List of arrays of y values paired with model name
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
        split_model= model.name in self._l_plot_components

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
        return float(par.value().numpy())
    #----------------------------------------
    def _get_color(self, name : str) -> str:
        '''
        Returns name of color associated to PDF component
        OR default color
        '''
        if name in self._col:
            return self._col[name]

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
        Returns array of y coordinates for array of x corrdinates
        and a given PDF
        '''
        try:
            tensor : tf.Tensor = pdf.pdf(x = xs)
        except Exception as exc:
            log.info(f'X values: {xs}')
            self._print_data()
            raise ValueError('Cannot evaluate PDF') from exc

        rng= self.plot_range
        ys = tensor.numpy()
        ys = ys / float(pdf.integrate(limits = rng).numpy())

        bin_area = ys * self.scan_width
        area = float(bin_area.sum())
        if not math.isclose(area, 1, abs_tol=0.01):
            raise ValueError(f'{pdf.name} not normalized to unity but {area:.3f} in {rng}')

        return ys
    #----------------------------------------
    def _plot_full_model(
        self,
        ax        : Axes,
        model     : zpdf,
        linestyle : str = '-') -> None:
        '''
        Plots full model when running in stack = False mode
        '''
        if self._l_blind is not None:
            log.debug(f'Blinding: {model.name}')
            return

        xs   = self._get_xcoor(rng = self.plot_range)
        ys   = self._evaluate_pdf(pdf = model, xs = xs)
        name = model.name

        ax.plot(
            xs, 
            ys * self.scale, 
            ls   = linestyle, 
            label= self._leg.get(name, name), 
            color= self._col.get(name))
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
    @property
    def scale(self) -> float:
        '''
        Number needed to scale scanned PDF array to match data normalization
        '''
        bin_size  = self.plot_width / self.nbins
        plot_area = bin_size * self.plot_yield

        corr      = self.norm_yield / self.plot_yield
        scale     = self.scan_width * corr * plot_area

        return scale / self.scan_width 
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
        return sut.range_from_obs(obs = self.norm)
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
        if self._plot_range is None:
            raise ValueError('Plot range not initialized')

        return self._plot_range
    #----------------------------------------
    @property
    def nbins(self) -> int:
        '''
        Number of bins meant for plots
        '''
        if self._nbins is None:
            raise ValueError('Number of bins not initialized')

        return self._nbins
    #----------------------------------------
    @property
    def plot_width(self) -> float:
        '''
        Width of region
        '''
        lower, upper = self.plot_range

        return upper - lower
    #----------------------------------------
    @property
    def scan_width(self) -> float:
        '''
        Distance between points when sampling PDFs
        '''
        return self.plot_width / _NXPOINTS
    #----------------------------------------
    @gut.timeit
    def plot(
        self,
        title           : None | str                    = None,
        stacked         : bool                          = False,
        blind           : tuple[str,float,float] | None = None,
        no_data         : bool                          = False,
        ranges          : None | list[Range]            = None,
        nbins           : int                           = 100,
        unit            : str                           = r'$\rm{MeV}/\it{c}^{2}$',
        xlabel          : str                           = '',
        ylabel          : str                           = '',
        d_leg           : dict[str,str] | None          = None,
        d_col           : dict[str,str] | None          = None,
        plot_range      : Range | None                  = None,
        plot_components : list[str]          | None     = None,
        ext_text        : None | str                    = None,
        add_pars        : None | str | list[str]        = None,
        ymax            : None | float                  = None,
        skip_pulls      : bool                          = False,
        pull_styling    : bool                          = True,
        yscale          : str                           = 'linear',
        axs             : None | tuple[Axes,...]        = None,
        figsize         : tuple[int,int]                = (13, 7),
        leg_loc         : str                           = 'best'):
        '''
        title (str)           : Title
        stacked (bool)        : If true will stack the PDFs
        ranges                : List of tuples with ranges if any was used for the fit, e.g. [(0, 3), (7, 10)]
        nbins                 : Bin numbers
        unit                  : Unit for x axis, default is MeV/c^2
        no_data (bool)        : If true data won't be plotted as well as pull
        xlabel                : xlabel
        ylabel                : ylabel
        d_leg                 : Customize legend
        d_col                 : Customize color
        plot_range            : Tuple with lower and upper bound for plot
        pull_styling(bool)    : Will add lines at +/-3 and set range to +/-5 for pull plots, by default True
        plot_components (list): List of strings, with names of PDFs, which are expected to be sums of PDFs and whose components should be plotted separately
        ext_text              : Text that can be added to plot
        add_pars (list|str)   : List of names of parameters to be added or string with value 'all' to add all fit parameters. If this is used, plot won't use LHCb style.
        skip_pulls(bool)      : Will not draw pulls if True, default False
        ymax (float)          : Optional, if specified will be used to set the maximum in plot
        blind                 : PDF name for the signal if blinding is needed, followed by blinding range, min and max.
        figsize (tuple)       : Tuple with figure size, default (13, 7)
        leg_loc (str)         : Location of legend, default 'best'
        yscale (str)          : Scale for y axis of main plot, either log or linear
        '''
        stacked                 = False if not isinstance(self.total_model, zfit.pdf.SumPDF) else stacked
        self._figsize           = figsize
        self._leg_loc           = leg_loc
        self._plot_range        = sut.range_from_obs(self.norm) if plot_range      is None else plot_range
        self._l_plot_components = []                            if plot_components is None else plot_components
        self._leg               = {}                            if           d_leg is None else d_leg
        self._col               = {}                            if           d_col is None else d_col
        self.axs                = self._get_axis(add_pars, skip_pulls) if axs is None else axs
        self._l_blind           = blind
        self._nbins             = nbins

        try:
            self.errors   = self._get_errors(ranges)
        except EmptyDataSet:
            log.warning('Found empty dataset, skipping plot')
            return

        if not stacked:
            log.debug('Plotting full model, for non-stacked case')
            self._plot_full_model(self.axs[0], self.total_model)

        log.debug('Plotting model components')
        self._plot_model_components(stacked = stacked)

        if not no_data:
            log.debug('Plotting data')
            self._plot_data(self.axs[0], ranges)

        if not skip_pulls and not no_data:
            log.debug('Plotting pulls')
            self._plot_pulls(ax = self.axs[1], l_range = ranges)

        text           = self._get_text(ext_text)
        xlabel, ylabel = self._get_labels(xlabel, ylabel, unit)

        self.axs[0].legend(title=text, fontsize=20, title_fontsize=20, loc=self._leg_loc)
        self.axs[0].set(xlabel=xlabel, ylabel=ylabel)

        self.axs[0].set_xlim(self._plot_range)

        if yscale is not None:
            self.axs[0].set_yscale(yscale)

        if title is not None:
            self.axs[0].set_title(title)

        if ymax is not None:
            ymin = _Y_MIN_LOG if yscale == 'log' else 0
            self.axs[0].set_ylim(bottom = ymin, top = ymax)

        if not skip_pulls:
            self.axs[1].set(xlabel=xlabel, ylabel="pulls")
            self.axs[1].set_xlim(*self.plot_range)

        for ax in self.axs:
            ax.label_outer()

        if pull_styling and not skip_pulls:
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
        self.plot(
            nbins           = cfg.nbins,
            stacked         = cfg.stacked,
            plot_components = cfg.plot_components,
            plot_range      = cfg.plot_range,
            ext_text        = cfg.ext_text,
            title           = cfg.title,
            skip_pulls      = cfg.skip_pulls,
            d_leg           = cfg.d_leg)
#----------------------------------------
