'''
Module with make_prec function, needed to create part reco electron templates from muon ones
'''
import typer

from rx_common      import Project, Qsq
from hqm.prec_maker import PrecMaker
from hqm.config     import TransferFunctionMakerConf
from dmu.generic    import Mode

mode_opt    = typer.Option(... , '-m', help = 'Mode in which to run')
proj_opt    = typer.Option(... , '-p', help = 'Project, e.g. rk')
src_opt     = typer.Option(... , '-s', help = 'Source q2-bin')
tgt_opt     = typer.Option(... , '-t', help = 'Target q2-bin')
binning_opt = typer.Option(... , '-b', help = 'String defining binning e.g. "block-1 mva_cmb-7 mva_prc-7"')
# ----------------------------------------------------------------------
def make_prec(
    mode    : Mode    = mode_opt,
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

    obj = PrecMaker(
        cfg     = cfg,
        binning = binning,
        project = project)
    obj.get_pdf(
        mode = mode,
        name = f'{source}_{target}')
# ----------------------------------------------------------------------
