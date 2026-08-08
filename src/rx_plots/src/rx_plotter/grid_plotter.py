'''
Module holding GridPlotter
'''
import random
import pandas            as pnd
import matplotlib.pyplot as plt

from functools import cached_property
from typing    import Final, Protocol
from pathlib   import Path
from dmu       import LogStore

log=LogStore.add_logger('rx_plots:grid_plotter')
_RANDOM_SIGMA : Final[float] = 0.2 # When randomizing grid, use value aroung 1 \pm 0.2
# --------------------------------
class GridProtocol(Protocol):
    '''
    Class representing grid-like object
    '''
    @cached_property
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
    def plot(self, path : Path, randomize : bool) -> None:
        '''
        Parameters
        ---------------
        path     : Path to directory where plot will be saved
        randomize: If True, will scale all values by a random number from Gauss(mu=1, sigma = 0.2)
        '''
        path.parent.mkdir(parents = True, exist_ok = True)

        df      = self.__grid.df
        pivoted = df.pivot(
                index  ='prc',
                columns='cmb',
                values ='yld')

        if randomize:
            scale   = random.gauss(mu = 1, sigma = _RANDOM_SIGMA)
            pivoted = scale * pivoted 

        v1 : float = pivoted.columns.min() # type: ignore
        v2 : float = pivoted.columns.max() # type: ignore
        v3 : float = pivoted.index.min()
        v4 : float = pivoted.index.max()

        plt.figure(figsize=(13, 10))
        plt.imshow(
            pivoted.values,
            aspect='auto',
            origin='lower',
            extent=(v1, v2, v3, v4),
            cmap='viridis',
            interpolation='bilinear',
        )

        if randomize:
            plt.title('Randomized yields vs WP')
        else:
            plt.title('Yields vs WP')

        plt.colorbar()
        plt.xlabel('MVA${}_{comb}$')
        plt.ylabel('MVA${}_{prec}$')
        plt.tight_layout()

        log.info(f'Saving to: {path}')

        plt.savefig(path)
        plt.close()
# --------------------------------
