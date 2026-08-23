'''
Module with Plotter class
'''
import numpy
import matplotlib.pyplot as plt

from pathlib        import Path
from dmu.stats      import zfit
from dmu.stats      import utilities as sut
from dmu.stats      import ZFitPlotterConf, ZFitPlotter
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

        size = len(array)
        plt.title(f'Entries: {size}')
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
        pdf = nll.model[0]
        dat = nll.data[0]

        self.plot_fit(name = name, pdf = pdf, data = dat)
    #-----------------------------
    def plot_fit(self, name : str, pdf : zpdf, data : numpy.ndarray | zfit.Data) -> None:
        plt_dir = _PLOT_DIR.get()
        if plt_dir is None:
            return

        if isinstance(data, numpy.ndarray):
            size = len(data)
        else:
            size = data.nevents

        cfg = ZFitPlotterConf.default()
        cfg = cfg.model_copy(update = {'title' : f'Entries = {size}'})

        ptr = ZFitPlotter(data = data, model = pdf)
        ptr.run(cfg = cfg)

        plt.savefig(plt_dir / f'{name}.png')
        plt.close()
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

        lower, upper = sut.range_from_obs(obs = pdf.space)

        xs = numpy.linspace(lower, upper, 1000)
        ys = pdf.pdf(xs)

        plt.scatter(xs, ys, s=2)
        plt.savefig(plt_dir / f'{name}.png')
        plt.close()
#-----------------------------
