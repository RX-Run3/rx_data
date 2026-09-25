'''
Module used to expose build_database function to CLI
'''
import typer

from dmu.generic    import Mode
from rx_common      import Project, Qsq
from hqm.data_store import DataStore
from hqm.config     import TransferFunctionMakerConf
from hqm.trfc       import TransferFunctionMaker

mode_opt  = typer.Option(..., '-m', help = 'Controls if transfer function will be remade, read, written or reused')
proj_opt  = typer.Option(..., '-p', help = 'Project, e.g. rk')
src_opt   = typer.Option(..., '-s', help = 'Source q2-bin')
tgt_opt   = typer.Option(..., '-t', help = 'Target q2-bin')
bin_opt   = typer.Option(..., '-b', help = 'Binning, e.g. "block-1 B_PT-3"')
# ----------------------------------------------------------------------
def make_trfc(
    mode    : Mode    = mode_opt,
    binning : str     = bin_opt,
    project : Project = proj_opt,
    source  : Qsq     = src_opt,
    target  : Qsq     = tgt_opt):
    '''
    Make transfer function
    '''
    cfg         = TransferFunctionMakerConf.load(
        binning = binning,
        project = project,
        source  = source,
        target  = target)

    with DataStore.selection(sel = cfg.binning.selection, update = False):
        obj         = TransferFunctionMaker(
            cfg     = cfg,
            project = project)
        obj.get_trf(mode = mode)
# ----------------------------------------------------------------------
