'''
Module used to expose build_database function to CLI
'''
import typer

from rx_common      import Block, Project, Qsq, Cuts
from hqm.data_store import DataStore
from hqm.config     import TransferFunctionMakerConf
from hqm.trfc       import TransferFunctionMaker 

update_opt= typer.Option(False, '-u', help = 'If used, will remake function even if already exists')
proj_opt  = typer.Option(...  , '-p', help = 'Project, e.g. rk')
src_opt   = typer.Option(...  , '-s', help = 'Source q2-bin')
tgt_opt   = typer.Option(...  , '-t', help = 'Target q2-bin')
block_opt = typer.Option(...  , '-b', help = 'E.g. 1')
# ----------------------------------------------------------------------
def make_trfc(
    update  : bool    = update_opt,
    block   : int     = block_opt,
    project : Project = proj_opt,
    source  : Qsq     = src_opt,
    target  : Qsq     = tgt_opt):
    '''
    Make transfer function
    '''
    blk = Block(value = block)

    cfgs        = TransferFunctionMakerConf.load(
        variable= 'none',
        project = project,
        source  = source,
        target  = target)

    sel = {'block' : f'block == {blk}'}

    for cfg in cfgs:
        with DataStore.selection(sel = sel, update = False):
            obj         = TransferFunctionMaker(
                cfg     = cfg,
                project = project,
                block   = blk)
            obj.get_trf(update = update)
# ----------------------------------------------------------------------
