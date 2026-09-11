'''
Module used to expose build_database function to CLI
'''
import typer

from contextlib     import ExitStack
from rx_common      import Block, Project, Qsq, Cuts
from hqm.prec_maker import PrecMaker
from hqm.data_store import DataStore
from hqm.config     import TransferFunctionMakerConf

update_opt  = typer.Option(False, '-u', help = 'If used, will remake function even if already exists')
proj_opt    = typer.Option(...  , '-p', help = 'Project, e.g. rk')
src_opt     = typer.Option(...  , '-s', help = 'Source q2-bin')
tgt_opt     = typer.Option(...  , '-t', help = 'Target q2-bin')
binning_opt = typer.Option(...  , '-b', help = 'String defining binning e.g. "block-1 mva_cmb-7 mva_prc-7"')
# ----------------------------------------------------------------------
def make_prec(
    update  : bool    = update_opt,
    project : Project = proj_opt,
    source  : Qsq     = src_opt,
    target  : Qsq     = tgt_opt,
    binning : str     = binning_opt):
    '''
    Make part reco PDF through transfer function and muon data 
    '''
    cfg = TransferFunctionMakerConf.load(
        binning  = binning, 
        project  = project,
        source   = source,
        target   = target)

    ctx1 = DataStore.selection(sel = cfg.binning.selection, update = False)
    with ExitStack() as stack:
        stack.enter_context(ctx1)

        obj = PrecMaker(
            cfg     = cfg, 
            binning = binning,
            project = project)
        obj.get_pdf(update = update)
# ----------------------------------------------------------------------
