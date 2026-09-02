'''
Module with Plotter class
'''
import numpy
import numpy.typing      as npt
import matplotlib.pyplot as plt

from pathlib        import Path
from dmu.stats      import zfit
from dmu.stats      import utilities as sut
from dmu.stats      import ZFitPlotterConf, ZFitPlotter

type Loss     = zfit.loss.ExtendedUnbinnedNLL
type zpdf     = zfit.pdf.BasePDF
type zdat     = zfit.data.Data
type NpFltArr = npt.NDArray[numpy.float64]
#-----------------------------
class Plotter:
    '''
    Class meant to hold plotting functionality 
    '''
    #-----------------------------
    def __init__(self, out_dir : Path):
        '''
        Parameters
        ----------------
        out_dir: Directory where all the plots will go
        '''
        self.__out_dir = out_dir
    #-----------------------------
    def __get_plot_range(self, pdf : zpdf, data : zdat | NpFltArr) -> tuple[float,float]:
        '''
        Parameters
        ---------------
        pdf : Model PDF
        data: Data to fit
        '''
        lower, _ = sut.range_from_obs(obs = pdf.space)
        if isinstance(data, zfit.Data):
            array = data.numpy()
        else:
            array = data

        upper = array.max() 

        return lower, upper
    #-----------------------------
    def plot_data(self, name : str, data : zfit.Data) -> None:
        '''
        Parameters
        -------------
        name : Used to build path, i.e. {PATH_DIR}/{name}.png
        data : Zfit data object 
        '''
        array = data.to_numpy()

        self.plot_array(name = name, array = array)
    #-----------------------------
    def plot_array(self, name : str, array : numpy.ndarray) -> None:
        '''
        Parameters
        -------------
        name : Used to build path, i.e. {PATH_DIR}/{name}.png
        array: Data to plot
        '''
        path = self.__out_dir / f'{name}.png'

        plt.hist(array, bins = 100)

        size = len(array)
        plt.title(f'Entries: {size}')
        plt.savefig(path)
        plt.close()
    #-----------------------------
    def plot_nll(
        self, 
        name : str, 
        nll  : Loss, 
        legs : dict[str,str]) -> None:
        '''
        Parameters
        -------------
        name : Used to build path, i.e. {PATH_DIR}/{name}.png
        Loss : Likelihood
        legs : Dictionary defining legend renaming
        '''
        pdf = nll.model[0]
        dat = nll.data[0]

        self.plot_fit(name = name, pdf = pdf, data = dat, legs = legs)
    #-----------------------------
    def plot_fit(
        self, 
        name : str, 
        pdf  : zpdf, 
        legs : dict[str,str],
        data : numpy.ndarray | zfit.Data) -> None:

        if isinstance(data, numpy.ndarray):
            size = len(data)
        else:
            size = data.nevents

        settings = {
            'd_leg'      : legs,
            'plot_range' : self.__get_plot_range(pdf = pdf, data = data),
            'title'      : f'Entries = {size}'}

        cfg = ZFitPlotterConf.default()
        cfg = cfg.model_copy(update = settings)

        ptr = ZFitPlotter(data = data, model = pdf)
        ptr.run(cfg = cfg)

        plt.savefig(self.__out_dir / f'{name}.png')
        plt.close()
    #-----------------------------
    def plot_model(self, name : str, pdf : zpdf) -> None:
        '''
        Parameters
        -------------
        name : Used to build path, i.e. {PATH_DIR}/{name}.png
        pdf  : PDF 
        '''
        lower, upper = sut.range_from_obs(obs = pdf.space)

        xs = numpy.linspace(lower, upper, 1000)
        ys = pdf.pdf(xs)

        plt.scatter(xs, ys, s=2)
        plt.savefig(self.__out_dir / f'{name}.png')
        plt.close()
#-----------------------------
