'''
Module used to run fits to resonant mode data
'''
import typer

from hqm.config     import CCbarRatioCalculatorConf
from hqm.data_store import DataStore
from hqm.ratc       import CCbarRatioCalculator
from rx_common      import Block, Component, Project, Qsq, Cuts

update_opt= typer.Option(False, '-u', help = 'If used, will remake function even if already exists')
proj_opt  = typer.Option(...  , '-p', help = 'Project, e.g. rk')
block_opt = typer.Option(...  , '-b', help = 'E.g. 1')
# ----------------------------------------------------------------------
def fit_resonant(
    update  : bool    = update_opt,
    blk     : int     = block_opt,
    project : Project = proj_opt):
    '''
    Run simultaneous fit to resonant modes
    '''
    cfgs  = CCbarRatioCalculatorConf.load(variable = 'none')
    cfg   = cfgs[0]
    block = Block(value = blk)

    sel : dict[Cuts,str] = {
        Cuts.prc  : f'mva_prc > 0.6',
        Cuts.cmb  : f'mva_cmb > 0.9',
        Cuts.block: f'block == {blk}'}

    with DataStore.selection(sel = sel, update = False):
        cal         = CCbarRatioCalculator(
            cfg     = cfg,
            block   = block,
            project = project)

        cal.get_ratio(update = update)
# ----------------------------------------------------------------------
