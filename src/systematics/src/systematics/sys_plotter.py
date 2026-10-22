'''
Module holding SysPlotter class
'''
import os
import pandas            as pnd
import matplotlib.pyplot as plt

from matplotlib.axes import Axes
from dmu.generic     import Serializable, utilities as gut
from functools       import cached_property
from pydantic        import BaseModel
from pathlib         import Path
from typing          import Final
from dmu             import LogStore

log = LogStore.add_logger('rx_stats:sys_plotter')

_MAX_FILLED_STYLE : Final[int] = 4
'''Make up to this number of histograms with fill style until
switching to stepfilled. Used for systematics histograms'''
# ---------------------------------
class LineCfg(BaseModel, frozen = True):
    style : str
    '''Line style'''
    width : float
    '''line width'''
    color : str
    '''line color'''
    skip  : bool = False
    '''If true will skip drawing this line, default False'''
# ---------------------------------
class SysAxis(BaseModel, frozen = True):
    '''
    Class meant to represent an axis when plotting systematics for POI
    '''
    label : str
    limits: tuple[float,float] | None 
    bins  : int 
# ---------------------------------
class SysPlotterCfg(BaseModel, Serializable, frozen = True):
    '''
    Data class meant to hold configurations for plotting of systematics
    '''
    name        : str
    '''
    String used to name output in {ANADIR}/toys/{NAME}/plots
    '''
    nominal     : str
    '''
    Name of nominal column in dataframes from toys, usually 'nominal'
    '''
    systematics : dict[str,str]
    '''
    systematics: Dictionary where:
        - Key  : Label used for systematic variation, for plots, usually latex.
        - Value: Column name in dataframe, e.g. alt_sig
    '''
    axes        : dict[str,SysAxis]
    '''
    Object describing, binning, ranges, etc
    '''
    vline       : LineCfg
    # ---------------------------------
    @classmethod
    def from_location(cls, loc : str) -> 'SysPlotterCfg':
        '''
        Parameters
        --------------
        log: String defining location of config WRT systematics_data

        Returns
        --------------
        Config object
        '''
        data = gut.load_data(package = 'systematics_data', fpath = loc)

        return cls(**data)
    # ---------------------------------
    @cached_property
    def out_dir(self) -> Path:
        '''
        Returns
        ---------------
        Directory where outputs will go
        '''
        ana_dir = os.environ['ANADIR']
        ana_dir = Path(ana_dir)

        out_dir = ana_dir / 'toys' / self.name / 'plots'

        out_dir.mkdir(parents=True, exist_ok=True)

        return out_dir
# ---------------------------------
class SysPlotter:
    '''
    Class in charge of plotting for each systematic:

    - Distributions of Delta POI in percent and the median across toys
    - Evolution of the median uncertainty in POI (error divided by value) 
      as the nuisance parameters are fixed 
    '''
    # ----------------------
    def __init__(
        self, 
        df : pnd.DataFrame, 
        cfg: SysPlotterCfg):
        '''
        Parameters
        -------------
        df : DataFrame with POI for each systematic and nominal 
        cfg: Configuration needed for plotting
        '''
        self._df = df
        self._cfg= cfg
    # ----------------------
    def _to_latex(self, data : dict[str,list[float|str]]) -> None:
        '''
        Makes latex table in out_path, replacing png with tex

        Parameters
        -------------
        data: Dictionary where
            Key  : Is a latex string describing systematic
            Value: Systematic in %
        '''
        df = pnd.DataFrame(data)

        def perc_func(value : float) -> str:
            return f'{value:.2f}'

        formatters = {
            'Value' : perc_func,
        } 

        # TODO: Remove ignore when:
        # https://github.com/pandas-dev/pandas-stubs/issues/1647
        # be fixed

        tex_path = self._cfg.out_dir / 'systematics.tex'
        log.info(f'Saving to: {tex_path}')
        with open(tex_path, 'w') as ofile:
            df.to_latex(                # type: ignore
                buf        = ofile, 
                index      = False, 
                formatters = formatters) # type: ignore
    # ----------------------
    def _add_vline(
        self, 
        ax  : Axes,
        val : float) -> None:
        '''
        Parameters
        -------------
        val: Value of x axis coordinate where to put the line
        ax : Axis where line has to be added
        '''
        cfg = self._cfg.vline
        if cfg.skip:
            return

        ax.axvline(
            x         = val, 
            color     = cfg.color,
            linestyle = cfg.style, 
            linewidth = cfg.width)
    # ----------------------
    def run(self) -> dict[str,float]:
        '''
        Runs plotting of systematics

        Returns
        ---------------
        dictionary where:

        Key  : Name of systematic
        Value: Median value of bias in %
        '''
        df = self._df
        nom= self._cfg.nominal
        xaxis : SysAxis = self._cfg.axes['x']
        yaxis : SysAxis = self._cfg.axes['y']

        syst = dict()
        data : dict[str,list[float|str]] = {'Systematic' : [], 'Value' : []}
        ax   = None
        counter = 1
        htype   = 'stepfilled' 
        alpha   = 0.7
        for label, sys in self._cfg.systematics.items():
            df[f'sys_{sys}'] = 100 * abs(df[nom] - df[sys]) / df[nom]

            if counter > _MAX_FILLED_STYLE:
                htype = 'step'
                alpha = 1

            ax = df[f'sys_{sys}'].plot.hist(
                x     = f'sys_{sys}', 
                range = xaxis.limits, 
                bins  = xaxis.bins, 
                alpha = alpha, 
                label = label, 
                histtype = htype,
                ax    = ax)

            med= df[f'sys_{sys}'].median()
            self._add_vline(val = med, ax = ax)

            syst[sys         ]= med
            data['Value'     ].append(float(med))
            data['Systematic'].append(label)

            counter += 1

        plt.legend()
        plt.xlabel(xaxis.label)

        plt.ylabel(yaxis.label)

        log.info(f'Saving in: {self._cfg.out_dir}/')
        plt.yscale('linear')
        plt.savefig(self._cfg.out_dir / 'models_lin.png')

        plt.yscale('log')
        plt.savefig(self._cfg.out_dir / 'models_log.png')

        plt.close()

        self._to_latex(data = data)

        return syst
# ---------------------------------
