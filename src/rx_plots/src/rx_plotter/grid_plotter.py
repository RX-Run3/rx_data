'''
Module holding GridPlotter
'''
import random
import numpy
import pandas            as pnd
import matplotlib.pyplot as plt

from typing            import Final
from pathlib           import Path
from dmu               import LogStore
from dmu.generic       import GridProtocol

log=LogStore.add_logger('rx_plots:grid_plotter')
_RANDOM_SIGMA : Final[float]       = 0.2 # When randomizing grid, use value aroung 1 \pm 0.2
_LEVELS       : Final[list[float]] = [0.05, 0.20, 0.30]
_STYLES       : Final[list[str  ]] = ['dotted', 'dashed', 'solid']
_XNAME        : Final[        str] = 'cmb'
_YNAME        : Final[        str] = 'prc'
_ZNAME        : Final[        str] = 'yld'
_MID_COLOR    : Final[      float] = 0.5
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

        df = self._plot_graph(randomize = randomize)
        self._plot_max(df = df)
        self._add_text(df = df)

        plt.xlabel('MVA${}_{comb}$')
        plt.ylabel('MVA${}_{prec}$')
        plt.tight_layout()

        log.info(f'Saving to: {path}')

        plt.savefig(path)
        plt.close()
    # -------------------
    def _plot_max(self, df : pnd.DataFrame) -> None:
        '''
        Parameters
        ----------------
        df: Pivoted dataframe
        '''
        arr_x = df.index.to_numpy()
        arr_y = df.columns.to_numpy()
        arr_z = df.values

        ix, iy = numpy.unravel_index(numpy.argmax(arr_z), arr_z.shape)
        y = arr_x[ix]
        x = arr_y[iy]

        plt.scatter([x], [y], color='red', s=200, zorder=5)
        plt.annotate(
            f'({x:.2f}, {y:.2f})',
            xy        = (x, y),
            xytext    = (-100, -40),
            fontsize  = '20',
            textcoords= 'offset points',
            color='red')
    # -------------------
    def _plot_graph(self, randomize : bool) -> pnd.DataFrame:
        df      = self.__grid.df
        pivoted = df.pivot(
            index  =_YNAME,
            columns=_XNAME,
            values =_ZNAME)

        if randomize:
            scale   = random.gauss(mu=1, sigma=_RANDOM_SIGMA)
            pivoted = scale * pivoted

        arr_x = pivoted.columns.to_numpy()
        arr_y = pivoted.index.to_numpy()
        arr_z = pivoted.values

        def edges(vals):
            mid = (vals[1:] + vals[:-1]) / 2
            first = vals[0] - (mid[0] - vals[0])
            last  = vals[-1] + (vals[-1] - mid[-1])
            return numpy.concatenate([[first], mid, [last]])

        x_edges = edges(arr_x)
        y_edges = edges(arr_y)

        plt.figure(figsize=(13, 10))
        mesh = plt.pcolormesh(
            x_edges, y_edges, arr_z,
            cmap='viridis', shading='flat')
        plt.colorbar(mesh)

        if randomize:
            plt.title('Randomized yields vs WP')
        else:
            plt.title('Yields vs WP')

        return pivoted
    # -------------------
    def _add_text(self, df : pnd.DataFrame) -> None:
        arr_x = df.columns.to_numpy()
        arr_y = df.index.to_numpy()
        arr_z = df.values

        zmin  = numpy.nanmin(arr_z)
        zmax  = numpy.nanmax(arr_z)
        for i, y in enumerate(arr_y):
            for j, x in enumerate(arr_x):
                val   = arr_z[i, j]
                norm  = (val - zmin) / (zmax - zmin)
                color = 'black' if norm > _MID_COLOR else 'white'
                plt.text(
                    x, y,
                    f'{val:.2f}',
                    ha='center', va='center',
                    zorder = 6 , alpha=0.8,
                    color=color, fontsize=14)
# --------------------------------
