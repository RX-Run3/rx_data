'''
Module holding PrecMaker class
'''
import numpy
import numpy.typing as npt

from dmu.stats      import zfit
from typing         import Final
from dmu            import LogStore
from hqm.config     import TransferFunctionMakerConf
from hqm.data_store import DataStore
from rx_common      import Block, Component, Mass, Cuts, Trigger

from hqm.trfc import TransferFunction

type zobs     = zfit.Space
type zpdf     = zfit.pdf.BasePDF
type NpFltArr = npt.NDArray[numpy.float64]

log=LogStore.add_logger('hqm:prec_maker')

_FFT_NPT     : Final[int]       = 2000
_DATA_SAMPLE : Final[Component] = Component.data_24
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

        with DataStore.selection(sel = sel, update = True):
            obj = DataStore(
                trig= self.__trig,
                comp= _DATA_SAMPLE,
                qsq = qsq)

        arr_raw, _ = obj.get_array(mass = Mass.bp_bcor)

        return arr_raw
    # -------------------------
    def __get_muon_pdf(self) -> zpdf:
        '''
        Returns
        -------------
        KDE representing muon part reco
        '''
        arr_mass = self.__get_masses()
        pdf      = zfit.pdf.KDE1DimExact(
            obs  = self.__cfg.observable.kde_obs,
            data = arr_mass)

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
    def get_pdf(self, name : str = 'prec') -> zpdf:
        '''
        Return
        -----------
        Zfit PDF
        '''
        pdf_mm = self.__get_muon_pdf()
        trf    = self.__get_trfc()

        pdf = zfit.pdf.FFTConvPDFV1(
            obs   = self.__cfg.observable.fit_obs,
            func  = pdf_mm,
            kernel= trf.pdf,
            name  = name,
            n     = _FFT_NPT)

        return pdf
# -----------------------------------
