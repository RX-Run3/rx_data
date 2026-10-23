'''
Module holding UncertaintyChecker class
'''
import os
import numpy
import pandas            as pnd
import matplotlib.pyplot as plt

from functools   import cached_property
from pathlib     import Path
from pydantic    import BaseModel
from dmu         import LogStore
from dmu.generic import Serializable

log=LogStore.add_logger('rx_stats:uncertainty_checker')
# -----------------------------
class UncertaintyCheckerCfg(BaseModel, Serializable, frozen = True):
    '''
    Class meant to hold configuration
    '''
    name   : str
    alpha  : float

    xlabel : str
    ylabel : str

    yrange : tuple[float,float]

    title  : str

    labels          : dict[str,str]
    xlabel_rotation : int
    # -------------------------
    @cached_property
    def out_dir(self) -> Path:
        '''
        Returns directory path where ouput should go
        '''
        ana_dir = os.environ['ANADIR']
        ana_dir = Path(ana_dir)

        out_dir = ana_dir / 'toys' / self.name / 'plots'

        out_dir.mkdir(parents = True, exist_ok = True)

        return out_dir
# -----------------------------
class UncertaintyChecker:
    '''
    Class meant to use toys made by SystematicsCalculator to:

    - Assess source of uncertainties in nominal model
    '''
    # ----------------------
    def __init__(
        self, 
        df : pnd.DataFrame,
        cfg: UncertaintyCheckerCfg):
        '''
        Parameters
        -------------
        df: DataFrame with information of POI as parameters were fixed.
        Should have columns:
        {'Error', 'Gen', 'Fixed', 'nFixed'}

        cfg: Object holding configuration
        '''
        self._check_df(df = df)

        self._df = df
        self._cfg= cfg
    # ----------------------
    def _check_df(self, df : pnd.DataFrame) -> None:
        '''
        Parameters
        -------------
        df: Pandas dataframe
        '''
        fail = False
        for col in ['nFixed', 'Fixed']:
            if col not in df.columns:
                log.error(col)
                fail = True

        if not fail:
            return

        for col in df.columns:
            log.info(col)

        raise ValueError('Columns missing')
    # ----------------------
    def _get_uncertainty(self, df : pnd.DataFrame) -> tuple[float,float,float]:
        '''
        Parameters
        -------------
        df: Pandas dataframe for a set of toys ran with a given number of floating parameters 
        i.e. with columns:
        {'Error', 'Gen', 'Fixed', 'nFixed'}
    
        Returns
        -------------
        Uncertainty in POI, upper and lower 68% CL in %
        '''
        unc = 100 * df['Error'] / df['Gen']
        sdt = unc.std()
        med = unc.median()
        lo  = med - sdt
        hi  = med + sdt

        return lo, hi, med
    # ----------------------
    def run(self) -> None:
        '''
        Makes plots
        '''
        med_unc   = []
        low_unc   = []
        upper_unc = []
        par_fixed = []

        df = self._df.sort_values(by = 'nFixed', ascending = True)
        for fix_par, df_fix in df.groupby('Fixed', sort = False):
            low, upper, median = self._get_uncertainty(df = df_fix)
            fix_par_str        = str(fix_par)
            par_label          = self._cfg.labels.get(fix_par_str, fix_par_str)

            med_unc.append(median)
            low_unc.append(low)
            upper_unc.append(upper)
            par_fixed.append(par_label)

        _, ax = plt.subplots()

        plt.plot(par_fixed, med_unc)
        ax.fill_between(
            x    = par_fixed,
            y1   = low_unc,
            y2   = upper_unc,
            alpha= self._cfg.alpha,
            label= None)

        ax.set_title(self._cfg.title)
        ax.set_xlabel(self._cfg.xlabel)
        ax.set_ylabel(self._cfg.ylabel)
        ax.set_ylim(self._cfg.yrange)
        ax.legend()
        plt.xticks(rotation=self._cfg.xlabel_rotation)
        plt.grid()

        log.info(f'Saving to: {self._cfg.out_dir}')
        plt.savefig(self._cfg.out_dir / 'uncertainties.png')
        plt.close()
# -----------------------------
