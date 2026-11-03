'''
Module with DatasetSummary class
'''
import re
import os
import pandas as pnd

from pathlib   import Path
from typing    import Final
from dmu       import LogStore
from rx_common import Qsq, Trigger, Component, Brem

_ANADIR      : Final[Path]      = Path(os.environ['ANADIR'])
_BLOCK_REGEX : Final[str]       = r'\d{3}_\d{3}_b(\d)' # Used to extract block from path
_COLUMNS     : Final[list[str]] = ['Passed', 'cut']    # Pick up these columns for each fit

log=LogStore.add_logger('fitter:dataset_summary')
# ----------------------------------------------
class DatasetSummary:
    '''
    Class meant to tabulate statistics for samples that were dropped from fits:

    - Pick up statistics associated to dataset used in fits
    - Build dataframe from statistics

    DataFrame contains columns:

    Block     : From 1 to 8
    Brem      : Brem category
    Component : MC sample
    Statistics: Number of candidate that pass cut

    The index is the name of the cut
    '''
    # ----------------------------------------------
    def __init__(self, name : str, trigger : Trigger):
        '''
        Parameters
        -----------------
        name : Name of fit, e.g. reso-dtf
        '''
        self.__name    = name
        self.__trigger = trigger
    # ----------------------------------------------
    def __has_fit(self, path : Path) -> bool:
        '''
        Parameters
        ----------------
        path : Path to data.md file

        Returns
        ----------------
        True if there is a fit associated to this path
        '''
        pars_path = path.parents[2] / 'fit' / path.parent.name / 'parameters.yaml'

        return pars_path.exists()
    # ----------------------------------------------
    def __find_paths(self) -> list[Path]:
        '''
        Returns
        -----------------
        List of paths to data.md files for low statistics fits
        '''
        log.info('Finding paths')

        root_pattern = f'fits/data/{self.__name}/*/*/{self.__trigger.project}/{self.__trigger.channel}/**/data.md'
        all_paths    = list(_ANADIR.rglob(pattern = root_pattern))

        if not all_paths:
            raise ValueError(f'No files found in: {_ANADIR/root_pattern}')

        npaths = len(all_paths)
        log.info(f'Found {npaths} paths')

        no_fit_paths = [ path for path in all_paths if not self.__has_fit(path = path) ]

        npaths_nofit = len(no_fit_paths)
        log.info(f'Found {npaths_nofit} paths not associated to any fit')

        return no_fit_paths
    # ----------------------------------------------
    def __block_from_path(self, path : Path) -> int:
        '''
        Parameters
        ----------------
        path: Path to file

        Returns
        ----------------
        Integer representing block
        '''
        mtch = re.search(pattern = _BLOCK_REGEX, string = str(path))
        if not mtch:
            raise ValueError(f'Cannot extract block from: {path}')

        val = mtch.group(1)

        return int(val)
    # ----------------------------------------------
    def __col_from_path(self, path : Path) -> pnd.DataFrame:
        '''
        Parameters
        ---------------
        path: Path to data.md

        Returns
        ---------------
        Tuple with:

        - Name of component as latex
        - Pandas series with statistics as content and cut as index
        '''
        log.debug(f'Reading: {path}')

        df          = self.markdown_to_df(path = path)
        df          = df[_COLUMNS]
        sample      = Component.from_path(path = path)
        df['q2bin'] = Qsq.from_path(path = path)
        df['Block'] = self.__block_from_path(path = path)
        df['Brem' ] = str(Brem.from_path(path = path))
        df['Sample']= sample.value

        return df
    # ----------------------------------------------
    @staticmethod
    def markdown_to_df(path : Path) -> pnd.DataFrame:
        '''
        Parameters
        -------------------
        path: Path to file with markdown

        Returns
        -------------------
        Pandas dataframe
        '''
        df = pnd.read_csv(path, sep = '|', skipinitialspace = True)
        df.columns = df.columns.str.strip()
        df = df.dropna(axis=1, how='all')
        df = df.iloc[1:].reset_index(drop=True)

        return df
    # ----------------------------------------------
    def get_df(self) -> pnd.DataFrame:
        '''
        Returns
        -------------
        dataframe with statistics
        '''
        paths = self.__find_paths()
        dfs   = [ self.__col_from_path(path = path) for path in paths ]

        return pnd.concat(dfs)
# ----------------------------------------------
