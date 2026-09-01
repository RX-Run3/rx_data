'''
Module used to expose build_database function to CLI
'''
import typer

from contextlib     import ExitStack
from rx_common      import Block, Trigger, Qsq, Cuts
from hqm.prec_maker import PrecMaker
from hqm.data_store import DataStore
from hqm.config     import TransferFunctionMakerConf

update_opt= typer.Option(False, '-u', help = 'If used, will remake function even if already exists')
trig_opt  = typer.Option(...  , '-T', help = 'Trigger, e.g. rk_ee_os')
src_opt   = typer.Option(...  , '-s', help = 'Source q2-bin')
tgt_opt   = typer.Option(...  , '-t', help = 'Target q2-bin')
block_opt = typer.Option(...  , '-b', help = 'E.g. 1')
# ----------------------------------------------------------------------
def make_prec(
    update  : bool    = update_opt,
    trigger : Trigger = trig_opt,
    source  : Qsq     = src_opt,
    target  : Qsq     = tgt_opt,
    blk     : int     = block_opt):
    '''
    Make part reco PDF through transfer function and muon data 
    '''
    block = Block(value = blk)

    cfg = TransferFunctionMakerConf.load(
        variable = 'none',
        project  = trigger.project,
        source   = source,
        target   = target)

    sel  = {Cuts.block : f'block == {block.value}'}
    ctx1 = DataStore.selection(sel = sel, update = False)

    with ExitStack() as stack:
        stack.enter_context(ctx1)

        obj = PrecMaker(
            cfg     = cfg[0], 
            block   = block,
            trigger = trigger)
        obj.get_pdf(update = update)
# ----------------------------------------------------------------------
