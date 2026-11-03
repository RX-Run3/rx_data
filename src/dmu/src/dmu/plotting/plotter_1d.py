'''
Module containing plotter class
'''
import math
import numpy
import matplotlib.pyplot as plt

from hist         import Hist
from omegaconf    import DictConfig
from ROOT         import RDF
from scipy.stats  import norm
from dmu          import LogStore
from dmu.generic  import naming
from .plotter     import Plotter
from .fwhm        import FWHM

log = LogStore.add_logger('dmu:plotting:Plotter1D')

CategoryData = dict[str, dict[str, numpy.ndarray]]
# --------------------------------------------
class Plotter1D(Plotter):
    '''
    Class used to plot columns in ROOT dataframes
    '''
    # --------------------------------------------
    def __init__(self, d_rdf : dict[str, RDF.RNode], cfg : DictConfig):
        '''
        Parameters:

        d_rdf (dict): Dictionary mapping the kind of sample with the ROOT dataframe
        cfg   (dict): Dictionary with configuration, e.g. binning, ranges, etc
        '''
        super().__init__(d_rdf=d_rdf, cfg=cfg)

        self._data : CategoryData = self._get_data()
    # ----------------------
    def _get_data(self) -> CategoryData:
        '''
        Returns
        -------------
        Dictionary with:
        Key  : Category of data to plot
        Value: Dictionary with:
            Key  : Variable name
            Value: Numpy array with values of variable
        '''
        variables = list(self._cfg.plots)
        log.info(f'Will pick: {variables}')
        data : CategoryData = {}

        log.info('Picking up data from dataframe:')
        for category, rdf in self._d_rdf.items():
            log.info(category)
            data[category] = rdf.AsNumpy(variables)

        # Swap keys, inner is variable, outer is category
        data_swap : CategoryData = {}
        for category, d_var in data.items():
            for variable, array in d_var.items():
                if variable not in data_swap:
                    data_swap[variable] = {}

                data_swap[variable][category] = array

        return data_swap
    #-------------------------------------
    def _get_labels(self, var : str) -> tuple[str,str]:
        if 'labels' not in self._cfg['plots'][var]:
            return var, 'Entries'

        xname, yname = self._cfg['plots'][var]['labels' ]

        return xname, yname
    #-------------------------------------
    def _is_normalized(self, var : str) -> bool:
        d_cfg     = self._cfg['plots'][var]
        normalized=False
        if 'normalized' in d_cfg:
            normalized = d_cfg['normalized']

        return normalized
    #-------------------------------------
    def _get_binning(self, var : str, d_data : dict[str, numpy.ndarray]) -> tuple[float, float, int]:
        d_cfg  = self._cfg['plots'][var]
        minx, maxx, bins = d_cfg['binning']

        minx      = float(minx)
        maxx      = float(maxx)
        are_close = numpy.isclose(minx, maxx, 1e-12)

        if maxx < minx and not are_close:
            raise ValueError(f'Wrong bounds for variable {var}: [{minx:.3e}, {maxx:.3e}]')

        if are_close:
            log.info(f'Bounds not set for {var}, will calculated them')
            minx, maxx = self._find_bounds(d_data = d_data, qnt=minx)
            log.info(f'Using bounds [{minx:.3e}, {maxx:.3e}]')
        else:
            log.debug(f'Using bounds [{minx:.3e}, {maxx:.3e}]')

        return minx, maxx, bins
    #-------------------------------------
    # TODO: Might need to move all plugins code elsewhere
    # and somehow register these plugins through config
    def _run_plugins(
            self,
            arr_val : numpy.ndarray,
            arr_wgt : numpy.ndarray,
            hst     : Hist,
            name    : str,
            varname : str) -> None:
        '''
        arr_val: Array of values of variable to plot
        arr_wgt: Array of weights
        hst    : Histogram, needed to plot extra information
        name   : Name of variable
        '''
        if 'plugin' not in self._cfg:
            log.debug('No plugins found')
            return

        if 'fwhm' in self._cfg['plugin']:
            if varname in self._cfg['plugin']['fwhm']:
                log.debug(f'FWHM plugin found for variable {varname}')
                cfg = self._cfg['plugin']['fwhm'][varname]
                self._run_fwhm(
                    arr_val = arr_val,
                    arr_wgt = arr_wgt,
                    hst     = hst,
                    name    = name,
                    varname = varname,
                    cfg     = cfg)

        if 'stats' in self._cfg['plugin']:
            if varname in self._cfg['plugin']['stats']:
                log.debug(f'stats plugin found for variable {varname}')
                cfg = self._cfg['plugin']['stats'][varname]
                self._run_stats(
                    arr_val = arr_val,
                    arr_wgt = arr_wgt,
                    name    = name,
                    varname = varname,
                    cfg     = cfg)

        if 'pulls' in self._cfg['plugin']:
            if varname in self._cfg['plugin']['pulls']:
                log.debug(f'pulls plugin found for variable {varname}')
                cfg = self._cfg['plugin']['pulls'][varname]
                [minx, maxx, _] = self._cfg['plots' ][varname]['binning']

                self._run_pulls(
                    arr_val = arr_val,
                    minx    = minx,
                    maxx    = maxx,
                    cfg     = cfg)

        if 'errors' in self._cfg['plugin']:
            if varname in self._cfg['plugin']['errors']:
                log.debug(f'errors plugin found for variable {varname}')
                cfg = self._cfg['plugin']['errors'][varname]

                self._run_errors(
                    arr_val = arr_val,
                    cfg     = cfg)
    # ----------------------
    def _run_errors(
        self,
        arr_val : numpy.ndarray,
        cfg     : DictConfig) -> None:
        '''
        Parameters
        -------------
        arr_val: Numpy array storing errors
        cfg    : Configuration
        '''
        color  = cfg.get('color' ,          'red')
        symbol = cfg.get('symbol', r'\varepsilon')
        median = numpy.nanmedian(arr_val)
        median = float(median)

        if 'format' not in cfg:
            val = f'{median:.3f}'
        else:
            fmt = cfg['format']
            val = fmt.format(median)

        label = rf'$\mathrm{{Med}}({symbol})={val}$'

        plt.axvline(x=median, ls=':', label=label, c=color)
    # ----------------------
    def _run_pulls(
        self,
        arr_val : numpy.ndarray,
        minx    : float,
        maxx    : float,
        cfg     : DictConfig) -> None:
        '''
        Parameters
        -------------------
        arr_val : Array of X axis values to plot
        cfg     : Configuration for the statistics plugin
        '''
        size   = len(arr_val)
        mask   = (arr_val > -4) & (arr_val < 4)

        mu, sg = norm.fit(arr_val[mask])
        em     = sg / math.sqrt(2 * (size - 1))
        es     = sg / math.sqrt(size)

        nbins  = 200
        arr_x  = numpy.linspace(minx, maxx, nbins)
        arr_y  = norm.pdf(arr_x, mu, sg)
        bw     = (maxx - minx) / nbins
        area   = bw * arr_y.sum()
        arr_y  = arr_y / area

        plt.plot(arr_x, arr_y, label='Fit', color='black')

        stats = rf'''
        $\mu={mu:.3f}\pm {em:.3f}$
        $\sigma={sg:.3f}\pm {es:.3f}$
        '''
        ax= plt.gca()
        ax.text(x=0.0, y = 0.80, s=stats, fontsize=30, transform=ax.transAxes)

        ax.axvline(x=mu     , ls=':', lw=1, c='r')
        ax.axvline(x=mu - sg, ls='-', lw=1, c='r')
        ax.axvline(x=mu + sg, ls='-', lw=1, c='r')
    # ----------------------
    def _trim_to_range(
        self,
        name: str,
        val : numpy.ndarray,
        wgt : numpy.ndarray) -> tuple[numpy.ndarray, numpy.ndarray]:
        '''
        Parameters
        -------------
        name: Name of variable
        val : Array of values in the 'x' axis
        wgt : Array of weights

        Returns
        -------------
        Tuple with the values and weights, but in the plotting range only
        '''
        [minx, maxx, _] = self._cfg['plots'][name]['binning']

        flags = (minx < val) & (val < maxx)
        val   = val[flags]
        wgt   = wgt[flags]

        return val, wgt
    #-------------------------------------
    def _run_stats(
        self,
        arr_val : numpy.ndarray,
        arr_wgt : numpy.ndarray,
        varname : str,
        name    : str,
        cfg     : dict[str,str]) -> None:
        '''
        Parameters
        -------------------
        arr_val : Array of X axis values to plot
        arr_wgt : Array of weights
        varname : Variable name
        name    : Name of the label, when plotting multiple distributions
        cfg     : Configuration for the statistics plugin
        '''
        arr_val, arr_wgt = self._trim_to_range(name=varname, val=arr_val, wgt=arr_wgt)

        this_title = ''
        data       = {}
        if 'sum' in cfg:
            form = cfg['sum']
            sumv = numpy.sum(arr_wgt)
            this_title += form.format(sumv) + '; '
            data['sum'] = sumv

        if 'mean' in cfg:
            form = cfg['mean']
            mean = numpy.average(arr_val, weights=arr_wgt)
            this_title += form.format(mean) + '; '
            data['mean'] = mean

        if 'rms'  in cfg:
            form = cfg['rms']
            mean = numpy.average(arr_val, weights=arr_wgt)
            rms  = numpy.sqrt(numpy.average((arr_val - mean) ** 2, weights=arr_wgt))
            this_title += form.format(rms ) + '; '
            data['rms'] = rms

        label = naming.clean_special_characters(name=name)
        self._data_to_json(data = data, name = f'stats_{varname}_{label}')

        self._title+= f'\n{name}: {this_title}'
    #-------------------------------------
    def _run_fwhm(
        self,
        arr_val : numpy.ndarray,
        arr_wgt : numpy.ndarray,
        hst     : Hist,
        varname : str,
        name    : str,
        cfg     : dict) -> None:

        arr_bin_cnt = hst.values()
        maxy = numpy.max(arr_bin_cnt)
        obj  = FWHM(cfg=cfg, val=arr_val, wgt=arr_wgt, maxy=maxy)
        fwhm = obj.run()

        form        = cfg['format']
        this_title  = form.format(fwhm)
        data        = {}

        if 'add_std' in cfg and cfg['add_std']:
            mu         = numpy.average(arr_val            , weights=arr_wgt)
            var        = numpy.average((arr_val - mu) ** 2, weights=arr_wgt)
            std        = numpy.sqrt(var)
            form       = form.replace('FWHM', 'STD')
            this_title+= '; ' + form.format(std)
            data       = {'mu' : mu, 'std' : std, 'fwhm' : fwhm}

        self._data_to_json(data = data, name = f'fwhm_{varname}_{name}')

        self._title+= f'\n{name}: {this_title}'
    #-------------------------------------
    def _plot_var(self, var : str) -> float:
        '''
        Will plot a variable from a dictionary of dataframes

        Parameters
        --------------------
        var: name of column

        Return
        --------------------
        Largest bin content among all bins and among all histograms plotted
        '''
        d_data           = self._data[var]
        minx, maxx, bins = self._get_binning(var, d_data)

        l_bc_all = []
        for name, arr_val in d_data.items():
            label        = self._label_from_name(name)
            arr_wgt      = self._d_wgt[name]
            arr_wgt      = self._normalize_weights(arr_wgt, var)
            hst          = Hist.new.Reg(bins=bins, start=minx, stop=maxx, name='x').Weight()
            hst.fill(x=arr_val, weight=arr_wgt)
            self._run_plugins(
                arr_val,
                arr_wgt,
                hst,  # type: ignore
                name,
                var)

            style = self._get_style_config(var=var, label=label)

            log.debug(f'Style: {style}')
            hst.plot(**style)

            l_bc_all    += hst.values().tolist()

        max_y = max(l_bc_all)

        return max_y
    # --------------------------------------------
    def _get_style_config(self, var : str, label : str) -> dict[str,str]:
        style = {
            'label'     : label,
            'histtype'  : 'errorbar',
            'linestyle' : 'none'}

        if 'styling' not in self._cfg['plots'][var]:
            log.debug(f'Styling not specified for {var}')
            return style

        if label     not in self._cfg['plots'][var]['styling']:
            log.debug(f'Styling not specified for {var}/{label}')
            return style

        custom_style = self._cfg['plots'][var]['styling'][label]
        style.update(custom_style)
        log.debug(f'Using custom styling for {var}/{label}')

        return style
    # --------------------------------------------
    def _label_from_name(self, name : str) -> str:
        if 'stats' not in self._cfg:
            return name

        d_stat = self._cfg['stats']
        if 'sumw' not in d_stat:
            return name

        form = d_stat['sumw']

        arr_wgt  = self._d_wgt[name]
        arr_wgt  = numpy.nan_to_num(arr_wgt, nan=0.0)
        sumw     = numpy.sum(arr_wgt)
        nentries = form.format(sumw)

        return f'{name:<15}{nentries:<10}'
    # --------------------------------------------
    def _normalize_weights(
        self,
        arr_wgt : numpy.ndarray,
        var     : str) -> numpy.ndarray:
        '''
        Parameters
        --------------
        arr_wgt : Array of weights
        var     : Plotting variable, needed to access normalization flag

        Returns
        --------------
        Array of weights, normalized to 1 or not
        '''
        cfg_var = self._cfg['plots'][var]
        if 'normalized' not in cfg_var:
            log.debug(f'Not normalizing for variable: {var}')
            return arr_wgt

        if not cfg_var['normalized']:
            log.debug(f'Not normalizing for variable: {var}')
            return arr_wgt

        [minx, maxx, nbins] = self._cfg['plots'][var]['binning']

        log.debug(f'Normalizing for variable: {var}')
        bw      = (maxx - minx) / nbins
        area    = bw * numpy.sum(arr_wgt)
        arr_wgt = arr_wgt / area

        return arr_wgt
    # --------------------------------------------
    def _style_plot(self, var : str, max_y : float) -> None:
        d_cfg  = self._cfg['plots'][var]
        yscale = d_cfg['yscale' ] if 'yscale' in d_cfg else 'linear'

        xname, yname = self._get_labels(var)
        plt.xlabel(xname)
        plt.ylabel(yname)
        plt.yscale(yscale)
        if yscale == 'linear':
            plt.ylim(bottom=0)

        title = self._title
        if 'title'      in d_cfg:
            this_title = d_cfg['title']
            title += f'\n {this_title}'

        title = title.lstrip('\n')

        plt.ylim(top=1.2 * max_y)
        plt.legend()
        plt.title(title)
    # --------------------------------------------
    def _plot_lines(self, var : str) -> None:
        '''
        Will plot vertical lines for some variables

        var (str) : name of variable
        '''
        var_cfg = self._cfg['plots'][var]
        if 'vline' in var_cfg:
            line_cfg = var_cfg['vline']
            plt.axvline(**line_cfg)
    # --------------------------------------------
    def run(self):
        '''
        Will run plotting
        '''

        fig_size = self._get_fig_size()
        for var in self._cfg.plots:
            self._title = ''
            fig, _= plt.subplots(figsize=fig_size)
            max_y = self._plot_var(var)
            self._style_plot(var, max_y)
            self._plot_lines(var)
            self._save_plot(var=var, fig=fig)
# --------------------------------------------
