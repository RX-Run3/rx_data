'''
Module with tests for PrecMaker class
'''
import pytest

from pathlib        import Path
from contextlib     import ExitStack
from hqm.config     import TransferFunctionMakerConf
from hqm.data_store import DataStore
from hqm.prec_maker import PrecMaker
from rx_common      import Block, Cuts, Trigger, Qsq

@pytest.mark.parametrize('source', [Qsq.jpsi, Qsq.psi2])
@pytest.mark.parametrize('target', [Qsq.jpsi, Qsq.psi2])
def test_resonant(tmp_path : Path, source : Qsq, target : Qsq):
    '''
    Simplest test
    '''
    trig  = Trigger.rk_ee_os
    block = Block(value = 5)

    cfg = TransferFunctionMakerConf.load(
        variable = 'none',
        project  = trig.project,
        source   = source,
        target   = target)

    sel  = {Cuts.block : f'block == {block.value}'}
    ctx1 = DataStore.selection(sel = sel, update = False)
    ctx2 = PrecMaker.diagnostics(path = tmp_path)

    with ExitStack() as stack:
        stack.enter_context(ctx1)
        stack.enter_context(ctx2)

        obj = PrecMaker(
            cfg     = cfg[0], 
            block   = block,
            trigger = trig)
        obj.get_pdf()

@pytest.mark.parametrize('source', [Qsq.jpsi, Qsq.psi2])
def test_rare(tmp_path : Path, source : Qsq):
    '''
    Simplest test
    '''
    trig  = Trigger.rk_ee_os
    block = Block(value = 5)

    cfg = TransferFunctionMakerConf.load(
        variable = 'none',
        project  = trig.project,
        source   = source,
        target   = Qsq.high)

    sel  = {Cuts.block : f'block == {block.value}'}
    ctx1 = DataStore.selection(sel = sel, update = False)

    with ExitStack() as stack:
        stack.enter_context(ctx1)

        obj = PrecMaker(
            cfg     = cfg[0], 
            block   = block,
            trigger = trig)
        obj.get_pdf()
