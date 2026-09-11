'''
Module used to run fits to resonant mode data
'''
import typer

from hqm.config     import CCbarRatioCalculatorConf
from hqm.data_store import DataStore
from hqm.ratc       import CCbarRatioCalculator
from rx_common      import Block, Component, Project, Qsq, Cuts

update_opt  = typer.Option(False, '-u', help = 'If used, will remake function even if already exists')
proj_opt    = typer.Option(...  , '-p', help = 'Project, e.g. rk')
binning_opt = typer.Option(...  , '-b', help = 'Binning, e.g. "block-1 mva_cmb-7 mva_prc-7"')
# ----------------------------------------------------------------------
def fit_resonant(
    update  : bool    = update_opt,
    binning : str     = binning_opt,
    project : Project = proj_opt):
    '''
    Run simultaneous fit to resonant modes
    '''
    cfg = CCbarRatioCalculatorConf.load(binning = binning)
    with DataStore.selection(sel = cfg.binning.selection, update = False):
        cal         = CCbarRatioCalculator(
            cfg     = cfg,
            binning = binning,
            project = project)

        cal.get_ratio(update = update)
# ----------------------------------------------------------------------
