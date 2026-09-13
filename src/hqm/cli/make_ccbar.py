'''
Module used to expose build_database function to CLI
'''
import typer
import matplotlib.pyplot as plt

from rx_common     import Project
from dmu.stats     import zfit
from dmu.stats     import ZFitPlotter, ZFitPlotterConf
from hqm.ccbar_pdf import CCbarPDFMaker

update_opt= typer.Option(False, '-u', help = 'If used, will remake function even if already exists')
proj_opt  = typer.Option(...  , '-p', help = 'Project, e.g. rk')
bin_opt   = typer.Option(...  , '-b', help = 'Binning, e.g. "block-1 B_PT-3"')
# ----------------------------------------------------------------------
def make_ccbar(
    update  : bool    = update_opt,
    binning : str     = bin_opt,
    project : Project = proj_opt):
    '''
    Make transfer function
    '''
    obs = zfit.Space('B_Mass', limits = (4600, 6500))
    ccb = CCbarPDFMaker(
        binning = binning,
        project = project)

    model= ccb.get_pdf(obs = obs, update = update)
    data = model.pdf.create_sampler(n = 10_000)

    cfg = ZFitPlotterConf.default()
    ptr = ZFitPlotter(model = model.pdf, data = data)
    ptr.run(cfg = cfg)
    plt.savefig(ccb.out_dir / 'model.png')
    plt.close()
# ----------------------------------------------------------------------
