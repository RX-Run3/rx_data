'''
Module used to expose build_database function to CLI
'''
import typer

from rx_common  import Block, Project, Qsq 
from hqm.config import TransferFunctionMakerConf
from hqm.trfc   import TransferFunctionMaker 

proj_opt  = typer.Option(..., '-p', help = 'Project, e.g. rk')
src_opt   = typer.Option(..., '-s', help = 'Source q2-bin')
tgt_opt   = typer.Option(..., '-t', help = 'Target q2-bin')
block_opt = typer.Option(..., '-b', help = 'E.g. 1')
# ----------------------------------------------------------------------
def make_trfc(
    block   : Block   = block_opt,
    project : Project = proj_opt,
    source  : Qsq     = src_opt,
    target  : Qsq     = tgt_opt):
    '''
    Make transfer function
    '''
    cfgs        = TransferFunctionMakerConf.load(
        variable= 'none',
        project = project,
        source  = source,
        target  = target)

    for cfg in cfgs:
        obj         = TransferFunctionMaker(
            cfg     = cfg,
            project = project,
            block   = block)

        trf=obj.get_trf()
        trf.to_json(path = cfg.out_dir / project / block / 'trfc.json')
# ----------------------------------------------------------------------
