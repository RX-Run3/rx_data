'''
Module holding CCbarConfTF class
'''
from hqm.binning   import BinningConf
from rx_common     import Qsq
from rx_common     import Trigger
from hqm.ccbar_pdf import CCbarPDF
from typing        import Literal, Final
from rx_common     import Block, Project
from dmu           import LogStore
from dmu.stats     import zfit
from rx_common     import Component
from rx_selection  import Registry

from .component_conf import ComponentConf

log=LogStore.add_logger('fitter:ccbar_conftf')

_COMPONENT : Final[Component] = Component.data_24
_TRIGGER   : Final[Trigger  ] = Trigger.rk_ee_os 
_QSQ       : Final[Qsq      ] = Qsq.high

type zpar = zfit.param.Parameter
type zpdf = zfit.pdf.BasePDF
# ------------------------------
class CCbarConfTF(ComponentConf, frozen = True):
    '''
    Class representing ccbar fit component obtained from transfer
    function approach, needed to:

    - Search ccbar PDF
    - Add them for all blocks
    '''
    from_sim_fit : Literal[False] = False
    '''
    Always false, this component does not come from SimFitter
    '''
    kind         : Literal['CCbarPDFTF']
    '''
    Version of `ccbar_pdf`
    '''
    # ------------------------------
    def _get_binning(self) -> str:
        '''
        Returns
        -------------
        String representing selection used to get PDF, e.g. 'mva_cmb-3 mva_prc-4'
        '''
        entry = Registry(
            qsq       = _QSQ,
            trigger   = _TRIGGER,
            component = _COMPONENT)

        sel     = { str(key) : val for key, val in entry.diff.items() }
        cfg     = BinningConf.load()
        binning = cfg.binning_from_sel(sel = sel)

        log.info(f'Using binning: {binning}')

        return binning
    # ------------------------------
    def _block_from_par(self, par : zpar) -> Block:
        '''
        Parameters
        ------------------
        par: Parameter representing block fraction

        Returns
        ------------------
        Block associated
        '''
        for block in Block.blocks():
            iblock = block.to_int()
            suffix = f'_b{iblock}'

            if not par.name.endswith(suffix):
                continue

            return block

        raise ValueError(f'Cannot extract block for parameter: {par.name}')
    # ------------------------------
    def _get_block_fractions(self, pdfs : dict[Component, zpdf]) -> dict[Block,zpar]:
        '''
        Parameters
        ----------------
        pdfs: Dictionary mapping component in fit to corresponding PDF

        Returns
        ----------------
        Dictionary mapping block to fraction parameter picked from one of the PDFs
        '''
        blocks = Block.blocks()

        for pdf in pdfs.values():
            if not isinstance(pdf, zfit.pdf.SumPDF):
                continue

            if len(pdf.pdfs) != len(blocks):
                continue

            return { self._block_from_par(par = par) : par for par in pdf.params.values() if not par.name.startswith('Composed_autoparam') }

        raise ValueError('Cannot find block fractions')
    # ------------------------------
    def get_pdf(
        self, 
        project : Project,
        pdfs    : dict[Component, zpdf]) -> zpdf:
        '''
        Parameters
        -----------------
        project: E.g. rk
        pdfs   : Dictionary mapping component to PDF in fitting model
                 This should include signal, which contains block fraction 
                 parameters, needed to parametrize this PDF

        Returns
        -----------------
        Zfit PDF representing sum of ccbar templates in high-q2 bin
        with block fraction parameters as used for signal
        '''
        d_frc = self._get_block_fractions(pdfs = pdfs)
        bins  = self._get_binning()

        d_pdf : dict[Block, zpdf] = dict()
        for block in Block.blocks():
            binning = f'block-{block} {bins}'

            path= CCbarPDF.get_path(
                binning = binning,
                project = project)
            obj = CCbarPDF.from_json(path = path)

            iblock     = block.to_int()
            pdf        = obj.get_pdf(
                name   = f'ccbar_block_{iblock}',
                suffix = f'b{iblock}')

            for par in pdf.get_params():
                par.floating = False

            d_pdf[block] = pdf

        fracs = [ d_frc[block] for block in Block.blocks() if block in d_frc ]
        ccpdf = list(d_pdf.values())

        return zfit.pdf.SumPDF(ccpdf, fracs) 
# ------------------------------
