'''
Module holding the MatrixPlotter class
'''
from typing import Annotated
import numpy
import numpy.typing      as npt
import matplotlib.pyplot as plt

from dmu.logging.log_store import LogStore

Array2D = Annotated[npt.NDArray[numpy.float64], '(n,n)']
log     = LogStore.add_logger('dmu:plotting:matrix')
# TODO: This class needs to become an interface to seaborn
#-------------------------------------------------------
class MatrixPlotter:
    '''
    Class used to plot matrices
    '''
    # -----------------------------------------------
    def __init__(self, mat : Array2D, cfg : dict):
        self._mat     = mat
        self._cfg     = cfg

        self._size    : int
        self._l_label : list[str]
    # -----------------------------------------------
    def _initialize(self) -> None:
        self._check_matrix()
        self._reformat_matrix()
        self._set_labels()
        self._mask_matrix()
    # -----------------------------------------------
    def _mask_matrix(self) -> None:
        if 'mask_value' not in self._cfg:
            return

        mask_val  = self._cfg['mask_value']
        log.debug(f'Masking value: {mask_val}')

        self._mat = numpy.ma.masked_where(self._mat == mask_val, self._mat)
    # -----------------------------------------------
    def _check_matrix(self) -> None:
        a, b = self._mat.shape

        if a != b:
            raise ValueError(f'Matrix is not square, but with shape: {a}x{b}')

        self._size = a
    # -----------------------------------------------
    def _set_labels(self) -> None:
        if 'labels' not in self._cfg:
            raise ValueError('Labels entry missing')

        l_lab = self._cfg['labels']
        nlab  = len(l_lab)

        if nlab != self._size:
            raise ValueError(f'Number of labels is not equal to its size: {nlab}!={self._size}')

        self._l_label = l_lab
    # -----------------------------------------------
    def _reformat_matrix(self) -> None:
        if 'upper' not in self._cfg:
            log.debug('Drawing full matrix')
            return

        upper = self._cfg['upper']
        if upper not in [True, False]:
            raise ValueError(f'Invalid value for upper setting: {upper}')

        if     upper:
            log.debug('Drawing upper matrix')
            self._mat = numpy.triu(self._mat, 0)
            return

        if not upper:
            log.debug('Drawing lower matrix')
            self._mat = numpy.triu(self._mat, 0)
            return
    # -----------------------------------------------
    def _set_axes(self, ax) -> None:
        ax.set_xticks(numpy.arange(self._size))
        ax.set_yticks(numpy.arange(self._size))

        ax.set_xticklabels(self._l_label)
        ax.set_yticklabels(self._l_label)

        rotation = 45
        if 'label_angle' in self._cfg:
            rotation = self._cfg['label_angle']

        plt.setp(ax.get_xticklabels(), rotation=rotation, ha="right", rotation_mode="anchor")
    # -----------------------------------------------
    def _draw_matrix(self) -> None:
        fsize = None
        if 'size' in self._cfg:
            fsize = self._cfg['size']

        if 'zrange' not in self._cfg:
            raise ValueError('z range not found in configuration')

        [zmin, zmax] = self._cfg['zrange']

        fig, ax = plt.subplots() if fsize is None else plt.subplots(figsize=fsize)

        palette = plt.cm.viridis #pylint: disable=no-member
        im      = ax.imshow(self._mat, cmap=palette, vmin=zmin, vmax=zmax)
        self._set_axes(ax)

        if 'format' in self._cfg:
            self._add_text(ax)
        else:
            log.debug('Not adding values to matrix but bar')
            fig.colorbar(im)

        if 'title' not in self._cfg:
            return

        title = self._cfg['title']
        ax.set_title(title)
        fig.tight_layout()
    # -----------------------------------------------
    def _add_text(self, ax):
        fontsize = 12
        if 'fontsize' in self._cfg:
            fontsize = self._cfg['fontsize']

        form = self._cfg['format']
        log.debug(f'Adding values with format {form}')

        for i_x, _ in enumerate(self._l_label):
            for i_y, _ in enumerate(self._l_label):
                try:
                    val  = self._mat[i_y, i_x]
                except:
                    log.error(f'Cannot access ({i_x}, {i_y}) in:')
                    print(self._mat)
                    raise

                if numpy.ma.is_masked(val):
                    text = ''
                else:
                    text = form.format(val)

                _ = ax.text(i_x, i_y, text, ha="center", va="center", fontsize=fontsize, color="k")
    # -----------------------------------------------
    def plot(self):
        '''
        Runs plotting, plot can be accessed through:

        ```python
        plt.show()
        plt.savefig(...)
        ```
        '''
        self._initialize()
        self._draw_matrix()
#-------------------------------------------------------
