'''
Module containing BandPlotter class
'''
import mplhep
import pandas            as pnd
import matplotlib.pyplot as plt

from pathlib  import Path
from pydantic import BaseModel
from dmu      import LogStore

log=LogStore.add_logger('dmu:plotting:band')
# ---------------------------------------
class Style(BaseModel):
    '''
    Class meant to configure styling of plot
    '''
    ylabel   : str
    yrange   : tuple[float,float]
    xrotation: int 
    alpha    : float
    color    : str
# ---------------------------------------
class BandPlotterConf(BaseModel):
    '''
    Configuration needed for BandPlotter
    '''
    out_dir : Path
    xname   : str
    styles  : dict[str,Style]
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
    def _style(self, parameter : str) -> tuple[float|None, str|None, str|None]:
        '''
        Parameters
        --------------
        parameter: Parameter name

        Returns
        --------------
        Tuple with:

        - alpha (opacity)
        - color
        '''
        if parameter not in self._cfg.styles:
            log.warning(f'No styling found for: {parameter}')
            return None, None, None

        style = self._cfg.styles[parameter]

        plt.ylim(style.yrange)
        plt.xticks(rotation = style.xrotation)

        return style.alpha, style.color, style.ylabel
    # ----------------------------
    def plot(self) -> None:
        '''
        Runs plotting
        '''
        for par, df_par in self._df.groupby('Parameter'):
            parameter = str(par)
            vals = df_par['Value']
            errs = df_par['Error']
            xval = df_par[self._cfg.xname]

            lower= vals - errs
            upper= vals + errs

            alpha, color, ylabel = self._style(parameter = parameter)

            plt.fill_between(
                x  = xval, 
                y1 = lower, 
                y2 = upper,
                alpha = alpha,
                color = color,
            )

            out_path = self._cfg.out_dir / f'{parameter}.png'
            if ylabel:
                plt.ylabel(ylabel)

            plt.savefig(out_path)
            plt.close()
# ---------------------------------------
