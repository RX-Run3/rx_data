'''
Module used to expose build_database function to CLI
'''
import typer
import matplotlib.pyplot as plt

from dmu.generic   import Mode
from rx_common     import Project
from dmu.stats     import zfit
from dmu.stats     import ZFitPlotter, ZFitPlotterConf
from hqm.ccbar_pdf import CCbarPDFMaker

mode_opt = typer.Option(..., '-m', help = 'Used to control how to make output')
proj_opt = typer.Option(..., '-p', help = 'Project, e.g. rk')
bin_opt  = typer.Option(..., '-b', help = 'Binning, e.g. "block-1 B_PT-3"')
# ----------------------------------------------------------------------
def make_ccbar(
    mode    : Mode    = mode_opt,
    binning : str     = bin_opt,
    project : Project = proj_opt):
    '''
    Make transfer function
    '''
    obs = zfit.Space('B_Mass', limits = (4600, 6500))
    ccb = CCbarPDFMaker(
        binning = binning,
        project = project)

    model= ccb.get_pdf(obs = obs, mode = mode)
    data = model.pdf.create_sampler(n = 10_000)

    legends = {
        'pdf_mc'    : 'Fully reconstructed',
        'part-reco' : 'Partially reconstructed'}

    cfg = ZFitPlotterConf.default()
    cfg = cfg.model_copy(update = {'d_leg' : legends})

    ptr = ZFitPlotter(model = model.pdf, data = data)
    ptr.run(cfg = cfg)
    plt.savefig(ccb.out_dir / 'model.png')
    plt.close()
# ----------------------------------------------------------------------
