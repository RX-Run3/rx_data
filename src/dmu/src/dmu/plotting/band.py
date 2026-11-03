'''
Module containing BandPlotter class
'''
import mplhep
import pandas            as pnd
import matplotlib.pyplot as plt

from typing   import Final
from pathlib  import Path
from pydantic import BaseModel
from dmu      import LogStore

log=LogStore.add_logger('dmu:plotting:band')
CATEGORY : Final[str] = 'Category'
PARAMETER: Final[str] = 'Parameter'
# ---------------------------------------
class Style(BaseModel):
    '''
    Class meant to configure styling of plot
    '''
    ylabel   : str
    yrange   : tuple[float|None,float|None]
    xrotation: int
    alpha    : float
# ---------------------------------------
class BandPlotterConf(BaseModel):
    '''
    Configuration needed for BandPlotter
    '''
    out_dir : Path
    size    : tuple[int,int]
    xname   : str
    styles  : dict[str,Style]
    labels  : dict[str,str]
    groups  : dict[str,list[str]]
# ---------------------------------------
class BandPlotter:
    '''
    Class meant to plot bands representing quantities
    with error bands
    '''
    # ----------------------------
    def __init__(
        self,
        cfg : BandPlotterConf,
        df  : pnd.DataFrame):
        '''
        Parameter
        ------------
        cfg: Configuration object
        df : DataFame with input data to plot
        '''
        self._cfg = cfg
        self._df  = df

        plt.style.use(mplhep.style.LHCb2)
    # ----------------------------
    def _style(self, parameter : str) -> tuple[float|None, str|None]:
        '''
        Parameters
        --------------
        parameter: Parameter name

        Returns
        --------------
        Tuple with:

        - alpha (opacity)
        - y-axis label
        '''
        if parameter not in self._cfg.styles:
            log.warning(f'No styling found for: {parameter}')
            return None, None

        style = self._cfg.styles[parameter]

        bottom, top = style.yrange
        if bottom:
            plt.ylim(bottom = bottom)
        if top:
            plt.ylim(top = top)

        plt.xticks(rotation = style.xrotation)

        return style.alpha, style.ylabel
    # ----------------------------
    def _plot_group(
        self,
        df         : pnd.DataFrame,
        par_name   : str,
        categories : list[str]) -> None:
        '''
        Parameters
        ----------------
        categories: List of categories in which this parameter is plotted
        '''
        plt.figure(figsize = self._cfg.size)
        for tmp, df_cat in df.groupby(CATEGORY):
            category = str(tmp)
            if category not in categories:
                log.error(f'Skipping: {category}')
                continue

            df_par = df_cat.query(f'{PARAMETER} == \"{par_name}\"')

            vals = df_par['Value']
            errs = df_par['Error']
            xval = df_par[self._cfg.xname]

            lower= vals - errs
            upper= vals + errs

            alpha, ylabel = self._style(parameter = par_name)

            plt.fill_between(
                x  = xval,
                y1 = lower, # type: ignore
                y2 = upper, # type: ignore
                alpha = alpha,
                label = self._cfg.labels[category],
            )

            if ylabel:
                plt.ylabel(ylabel)
    # ----------------------------
    def plot(self) -> None:
        '''
        Runs plotting
        '''
        for tmp, df_par in self._df.groupby(PARAMETER):
            par_name = str(tmp)
            for group, categories in self._cfg.groups.items():
                self._plot_group(
                    df         = df_par,
                    par_name   = par_name,
                    categories = categories)

                self._cfg.out_dir.mkdir(parents = True, exist_ok = True)
                out_path = self._cfg.out_dir / group / f'{par_name}.png'
                out_path.parent.mkdir(parents = True, exist_ok = True)

                plt.legend()
                log.info(f'Saving parameter summary to: {out_path}')
                plt.grid()
                plt.savefig(out_path)
                plt.close()
# ---------------------------------------
