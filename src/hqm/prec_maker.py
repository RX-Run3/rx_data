'''
Module holding PrecMaker class
'''
import numpy
import numpy.typing      as npt
import matplotlib.pyplot as plt

from pathlib        import Path
from dmu.stats      import ZFitPlotter, ZFitPlotterConf, zfit
from typing         import Final
from dmu            import LogStore
from dmu.stats      import SplinePDF
from hqm.config     import TransferFunctionMakerConf
from hqm.data_store import DataStore
from rx_common      import Block, Channel, Component, Mass, Cuts, Trigger
from hqm.trfc       import TransferFunction

type zobs     = zfit.Space
type zpdf     = zfit.pdf.BasePDF
type zcnv     = zfit.pdf.FFTConvPDFV1
type NpFltArr = npt.NDArray[numpy.float64]

log=LogStore.add_logger('hqm:prec_maker')

_FFT_NPT         : Final[int]       = 2000
_DATA_SAMPLE     : Final[Component] = Component.data_24
_MISSING_BLOCKS  : Final[set[int]]  = {4,3,2,1}   # blocks for which muon mass does not go all the way to 3.5 GeV
_PATCHING_BLOCK  : Final[int]       = 5           # will use this block instead of missing blocks
# -----------------------------------
class PrecMaker:
    '''
    Class meant to provide part reco template
    '''
    # -------------------------
    def __init__(
        self, 
        block   : Block,
        trigger : Trigger,
        cfg     : TransferFunctionMakerConf):
        '''
        Parameters
        ----------------
        block: Determines part of the data been processed
        cfg  : Configuration for transfer function 
        '''
        self.__trig = trigger
        self.__cfg  = cfg 
        self.__block= block
    # -------------------------
    def __get_masses(self) -> NpFltArr:
        '''
        Returns
        -----------
        Numpy array with floats representing masses 
        from low sideband in muon channel
        '''
        qsq  = self.__cfg.source
        mass = Mass.raw_from_project(project = self.__trig.project)

        sel            = dict()
        sel[Cuts.q2]   = f'(q2 > {qsq.lower_bound}) & (q2 < {qsq.upper_bound})'
        sel[Cuts.mass] = f'{mass} < 5180'

        if self.__block.to_int() in _MISSING_BLOCKS:
            log.warning(f'Using {_PATCHING_BLOCK} instead of {self.__block} block')
            sel[Cuts.block] = f'block == {_PATCHING_BLOCK}'

        trig        = Trigger.get_main_trigger(
            channel = Channel.mm,
            project = self.__trig.project)

        with DataStore.selection(sel = sel, update = True):
            obj = DataStore(
                trig= trig,
                comp= _DATA_SAMPLE,
                qsq = qsq)

        arr_raw, _ = obj.get_array(mass = Mass.bp_bcor)

        return arr_raw
    # -------------------------
    def __get_muon_pdf(self, out_dir : Path) -> zpdf:
        '''
        Parameters
        -------------
        out_dir: Directory where outputs will go

        Returns
        -------------
        KDE representing muon part reco
        '''
        arr_mass = self.__get_masses()
        pdf      = zfit.pdf.KDE1DimISJ(
            obs  = self.__cfg.observable.kde_obs,
            data = arr_mass)

        out_path = out_dir / 'fit.png'
        log.info(f'Saving to: {out_path}')

        cfg = ZFitPlotterConf.default()
        ptr = ZFitPlotter(data = arr_mass, model = pdf)
        ptr.run(cfg)
        plt.savefig(out_path)
        plt.close()

        return pdf
    # -------------------------
    def __get_trfc(self) -> TransferFunction:
        '''
        Returns
        --------------
        Transfer function
        '''
        path = self.__cfg.make_path(
            kind    = 'trfc',
            project = self.__trig.project,
            subdir  = f'block_{self.__block}/{self.__cfg.source}_to_{self.__cfg.target}',
            fname   = 'trfc.json')

        return TransferFunction.from_json(path = path)
    # -------------------------
    def __get_path(self) -> Path:
        '''
        Returns
        --------------
        Path to JSON file where PDF should be stored
        '''
        return self.__cfg.make_path(
            kind    = 'part-reco',
            project = self.__trig.project,
            subdir  = f'block_{self.__block}/{self.__cfg.source}_to_{self.__cfg.target}',
            fname   = 'part-reco.json')
    # -------------------------
    def get_pdf(self, name : str = 'prec') -> SplinePDF:
        '''
        Return
        -----------
        Zfit PDF for electron channel representing part reco background
        '''
        path = self.__get_path()
        if path.exists():
            return SplinePDF.from_json(path = path)

        pdf_mm = self.__get_muon_pdf(out_dir = path.parent)
        trf    = self.__get_trfc()

        pdf_ee = zfit.pdf.FFTConvPDFV1(
            obs   = self.__cfg.observable.fit_obs,
            func  = pdf_mm,
            kernel= trf.pdf,
            name  = name,
            n     = _FFT_NPT)

        pdf = SplinePDF.from_non_spline(pdf = pdf_ee)
        pdf.to_json(path = path)

        xs    = numpy.linspace(3500, 7000, num = 1000)
        ys_mm = pdf_mm.pdf(xs)
        ys_ee = pdf_ee.pdf(xs)

        out_path = path.parent / 'pdf.png'
        log.info(f'Saving to: {out_path}')
        plt.scatter(xs, ys_mm, s=1, label = 'Muon')
        plt.scatter(xs, ys_ee, s=1, label = 'Electron')
        plt.title(f'{self.__cfg.source.latex} to {self.__cfg.target.latex}')
        plt.legend()
        plt.grid()
        plt.savefig(out_path)
        plt.close()

        return pdf
# -----------------------------------
