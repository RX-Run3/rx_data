'''
Module holding GridPlotter
'''
import pandas            as pnd
import matplotlib.pyplot as plt

from typing  import Protocol
from pathlib import Path
from dmu     import LogStore

log=LogStore.add_logger('rx_plots:grid_plotter')
# --------------------------------
class GridProtocol(Protocol):
    '''
    Class representing grid-like object
    '''
    @property
    def df(self) -> pnd.DataFrame: ...
# --------------------------------
class GridPlotter:
    '''
    Generic plotter of objects holding grid-like information
    i.e. z vs x, y
    '''
    # -------------------
    def __init__(self, grid : GridProtocol):
        '''
        Parameters
        --------------
        grid: Gridlike object
        '''
        self.__grid = grid
    # -------------------
    def plot(self, path : Path) -> None:
        '''
        Parameters
        ---------------
        path: Path to directory where plot will be saved
        '''
        df      = self.__grid.df
        pivoted = df.pivot(
                index  ='prc',
                columns='cmb',
                values ='yld')

        v1 : float = pivoted.columns.min() # type: ignore
        v2 : float = pivoted.columns.max() # type: ignore
        v3 : float = pivoted.index.min()
        v4 : float = pivoted.index.max()

        plt.imshow(
            pivoted.values,
            origin='lower',
            extent=(v1, v2, v3, v4),
            cmap='viridis',
            interpolation='bilinear',
        )

        plt.title('Yields vs WP')
        plt.colorbar(label='z')
        plt.xlabel('MVA${}_{comb}$')
        plt.ylabel('MVA${}_{prec}$')
        plt.tight_layout()

        out_path = path / 'yields.png'
        log.info(f'Saving to: {out_path}')

        plt.savefig(out_path)
        plt.close()
# --------------------------------
