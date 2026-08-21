'''
Module with Plotter class
'''
import numpy
import matplotlib.pyplot as plt

from pathlib        import Path
from dmu.stats      import zfit
from contextlib     import contextmanager
from contextvars    import ContextVar

_PLOT_DIR : ContextVar[Path|None] = ContextVar('_PLOT_DIR', default = None)

Loss = zfit.loss.ExtendedUnbinnedNLL
zpdf = zfit.pdf.BasePDF
#-----------------------------
class Plotter:
    '''
    Class meant to hold plotting functionality 
    '''
    #-----------------------------
    @classmethod
    def plot(cls, path : Path):
        '''
        Parameters
        -----------------
        path: Path to directory where plots will be saved in this context
        '''
        path.mkdir(parents = True, exist_ok = True)

        @contextmanager
        def _context():
            token = _PLOT_DIR.set(path)
            try:
                yield
            finally:
                _PLOT_DIR.reset(token)

        return _context()
    #-----------------------------
    def plot_array(self, name : str, array : numpy.ndarray) -> None:
        '''
        Parameters
        -------------
        name : Used to build path, i.e. {PATH_DIR}/{name}.png
        array: Data to plot
        '''
        plt_dir = _PLOT_DIR.get()
        if plt_dir is None:
            return

        path = plt_dir / f'{name}.png'

        plt.hist(array, bins = 100)
        plt.savefig(path)
        plt.close()
    #-----------------------------
    def plot_nll(self, name : str, nll : Loss) -> None:
        '''
        Parameters
        -------------
        name : Used to build path, i.e. {PATH_DIR}/{name}.png
        Loss : Likelihood
        '''
        plt_dir = _PLOT_DIR.get()
        if plt_dir is None:
            return
    #-----------------------------
    def plot_model(self, name : str, pdf : zpdf) -> None:
        '''
        Parameters
        -------------
        name : Used to build path, i.e. {PATH_DIR}/{name}.png
        pdf  : PDF 
        '''
        plt_dir = _PLOT_DIR.get()
        if plt_dir is None:
            return
#-----------------------------
