'''
Module with tests for PrecMaker class
'''
import pytest

from pathlib        import Path
from contextlib     import ExitStack
from hqm.config     import TransferFunctionMakerConf
from hqm.data_store import DataStore
from hqm.prec_maker import PrecMaker
from rx_common      import Block, Cuts, Project, Qsq

# ------------------------------------------------------------
@pytest.mark.parametrize('source', [Qsq.jpsi, Qsq.psi2])
@pytest.mark.parametrize('target', [Qsq.jpsi, Qsq.psi2, Qsq.high])
def test_resonant(source : Qsq, target : Qsq):
    '''
    Simplest test
    '''
    proj  = Project.rk 
    blk   = 5
    block = Block(value = blk)

    cfg = TransferFunctionMakerConf.load(
        binning  = f'block-{blk}',
        project  = proj,
        source   = source,
        target   = target)

    ctx1 = DataStore.selection(sel = cfg.binning.selection, update = False)
    with ExitStack() as stack:
        stack.enter_context(ctx1)

        obj = PrecMaker(
            cfg     = cfg, 
            block   = block,
            project = proj)
        obj.get_pdf(update = True)
# ------------------------------------------------------------
