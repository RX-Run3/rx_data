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
from hqm.binning    import BinningConf
from hqm.config     import TransferFunctionMakerConf
from hqm.data_store import DataStore
from rx_common      import Channel, Component, Mass, Project, Trigger
from hqm.trfc       import TransferFunction
from dmu.generic    import Mode

type zobs     = zfit.Space
type zpdf     = zfit.pdf.BasePDF
type zcnv     = zfit.pdf.FFTConvPDFV1
type NpFltArr = npt.NDArray[numpy.float64]

log=LogStore.add_logger('hqm:prec_maker')

_FFT_NPT         : Final[int]       = 2000
_DATA_SAMPLE     : Final[Component] = Component.data_24
_MISSING_BLOCKS  : Final[set[int]]  = {4,3,2,1}   # blocks for which muon mass does not go all the way to 3.5 GeV
_PATCHING_BLOCK  : Final[int]       = 5           # will use this block instead of missing blocks
_PREC_MASS       : Final[int]       = 5180        # Below this mass, everything in the muon channel is part-reco
_MIN_ISJ         : Final[int]       = 1000        # Below this number of entries in the low muon sideband, will use KDE1DimExact
# -----------------------------------
class PrecMaker:
    '''
    Class meant to provide part reco template
    '''
    # -------------------------
    def __init__(
        self,
        binning : str,
        project : Project,
        cfg     : TransferFunctionMakerConf):
        '''
        Parameters
        ----------------
        binning: String defining binning
        cfg    : Configuration for transfer function
        project: E.g. rk or rkst, needed to extract masses,
        '''
        self.__proj = project
        self.__cfg  = cfg
        self.__sel  = self.__get_selection(binning = binning)
    # -------------------------
    def __get_selection(self, binning : str) -> dict[str,str]:
        '''
        Parameters
        -------------
        binning: String defining bin in which Prec template is needed

        Returns
        -------------
        Selection dictionary with:

        - q2 bin
        - Lower sideband cut
        - Overriding of block for blocks with missing low sideband
        '''
        bin_obj = BinningConf.load()
        bins    = bin_obj.from_str(binning)
        block   = bins.block
        qsq     = self.__cfg.source
        mass    = Mass.raw_from_project(project = self.__proj)

        sel         = bins.selection
        sel['q2'  ] = f'(q2 > {qsq.lower_bound}) & (q2 < {qsq.upper_bound})'
        sel['mass'] = f'{mass} < {_PREC_MASS}'

        if block.to_int() in _MISSING_BLOCKS:
            log.warning(f'Using {_PATCHING_BLOCK} instead of {block} block')
            sel['block'] = f'block == {_PATCHING_BLOCK}'

        return sel
    # -------------------------
    def __get_masses(self, out_dir : Path) -> NpFltArr:
        '''
        Parameters
        -----------
        out_dir: Directory where outputs go

        Returns
        -----------
        Numpy array with floats representing masses
        from low sideband in muon channel
        '''

        trig        = Trigger.get_main_trigger(
            channel = Channel.mm,
            project = self.__proj)

        arr_raw     = self.__get_array(
            out_dir = out_dir,
            trig    = trig)

        return arr_raw
    # -------------------------
    def __get_array(
        self,
        out_dir: Path,
        trig   : Trigger) -> NpFltArr:
        '''
        Parameters
        -------------
        out_dir: Directory where JSON file with selection will be saved
        trig   : Trigger
        '''
        with DataStore.selection(sel = self.__sel, update = True):
            obj = DataStore(trig= trig, comp = _DATA_SAMPLE)
            obj.save_selection(path = out_dir / 'muon_selection.json')

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
        arr_mass = self.__get_masses(out_dir = out_dir)
        nentries = len(arr_mass)

        if nentries > _MIN_ISJ:
            pdf      = zfit.pdf.KDE1DimISJ(
                obs  = self.__cfg.observable.wide_obs,
                data = arr_mass)
        else:
            pdf      = zfit.pdf.KDE1DimExact(
                obs  = self.__cfg.observable.wide_obs,
                data = arr_mass)

        out_path = out_dir / 'fit.png'
        log.info(f'Saving to: {out_path}')

        cfg = ZFitPlotterConf.default()
        cfg = cfg.model_copy(update = {'title' : f'Entries: {nentries}'})

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
            project = self.__proj,
            subdir  = f'{self.__cfg.source}_to_{self.__cfg.target}',
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
            project = self.__proj,
            subdir  = f'{self.__cfg.source}_to_{self.__cfg.target}',
            fname   = 'part-reco.json')
    # -------------------------
    def __plot_pdf(
        self,
        pdf_ee : zpdf,
        pdf_mm : zpdf,
        out_dir: Path) -> None:
        '''
        Parameters
        -------------
        pdf_ee/mm: PDF after/before transfer function
        out_dir  : Directory where outputs will go
        '''
        xs    = numpy.linspace(3500, 7000, num = 1000)
        ys_mm = pdf_mm.pdf(xs)
        ys_ee = pdf_ee.pdf(xs)

        ys_mm = ys_mm / ys_mm.numpy().sum()
        ys_ee = ys_ee / ys_ee.numpy().sum()

        out_path = out_dir / 'pdf.png'
        log.info(f'Saving to: {out_path}')
        plt.plot(xs, ys_mm, label = 'Muon')
        plt.plot(xs, ys_ee, label = 'Electron')
        plt.title(f'{self.__cfg.source.latex} to {self.__cfg.target.latex}')
        plt.legend()
        plt.grid()
        plt.savefig(out_path)
        plt.close()
    # -------------------------
    def get_pdf(
        self,
        mode : Mode,
        name : str) -> SplinePDF:
        '''
        Parameters
        ------------------
        update: If True will remake PDF fits, even if found already
        name  : Name of PDF

        Return
        -----------
        Zfit PDF for electron channel representing part reco background
        '''
        path = self.__get_path()
        mode.validate(path = path)

        if path.exists() and not mode.skip_reading:
            log.info(f'Part reco PDF found, loading: {path}')
            return SplinePDF.from_json(path = path, name = name)

        log.info('Part reco PDF not found, remaking it')
        pdf_mm = self.__get_muon_pdf(out_dir = path.parent)
        trf    = self.__get_trfc()

        pdf_ee = zfit.pdf.FFTConvPDFV1(
            obs   = self.__cfg.observable.mass_obs,
            func  = pdf_mm,
            kernel= trf.pdf,
            name  = name,
            n     = _FFT_NPT)

        self.__plot_pdf(
            pdf_mm = pdf_mm,
            pdf_ee = pdf_ee,
            out_dir= path.parent)

        pdf = SplinePDF.from_non_spline(pdf = pdf_ee)
        pdf.to_json(path = path)

        return pdf
# -----------------------------------
