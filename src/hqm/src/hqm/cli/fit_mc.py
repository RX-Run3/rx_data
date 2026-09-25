'''
Module used to expose build_database function to CLI
'''
import typer

from contextlib     import ExitStack
from rx_common      import Component, Qsq, Trigger
from dmu.stats      import zfit
from hqm.pdf_mc     import PdfBuilder
from hqm.data_store import DataStore
from hqm.binning    import BinningConf
from dmu.generic    import Mode

mode_opt   : Mode = typer.Option(...  , '-m', help = 'Mode in which outputs will be created')
use_dtf_opt= typer.Option(False, '-d', help = 'If used, will use q2_dtf in selection of data')
use_kde_opt= typer.Option(False, '-k', help = 'If used, will use KDE for fit')
smear_opt  = typer.Option(False, '-s', help = 'If used, will smear masses before applying selection')
trig_opt   = typer.Option(...  , '-t', help = 'Trigger, e.g. rk_ee_os')
comp_opt   = typer.Option(...  , '-c', help = 'Component, e.g. bpkpjpsiee')
qsq_opt    = typer.Option(...  , '-q', help = 'q2-bin fitted')
binning_opt= typer.Option(...  , '-b', help = 'Binning, e.g. block-3')
# ----------------------------------------------------------------------
def fit_mc(
    component : str     = comp_opt,
    mode      : Mode    = mode_opt,
    use_dtf   : bool    = use_dtf_opt,
    use_kde   : bool    = use_kde_opt,
    trigger   : Trigger = trig_opt,
    qsq       : Qsq     = qsq_opt,
    smear     : bool    = smear_opt,
    binning   : str     = binning_opt):
    '''
    Make part reco PDF through transfer function and muon data
    '''
    bin_obj  = BinningConf.load()
    bins     = bin_obj.from_str(binning)
    comp     = Component(component)

    qsq_name = 'q2_dtf' if use_dtf else 'q2'
    model    = 'kde'    if use_kde else 'parametric'

    sel      = bins.selection
    if trigger.is_electron:
        sel['brem'] = 'nbrem in [1, 2]'

    sel['q2'] = f'({qsq_name} > {qsq.lower_bound}) & ({qsq_name} < {qsq.upper_bound})'

    ctx1  = DataStore.smear_masses(value = smear)
    ctx2  = DataStore.selection(sel = sel, update = False)
    obs   = zfit.Space('B_Mass', limits = (4600, 6000))
    with ExitStack() as stack:
        stack.enter_context(ctx1)
        stack.enter_context(ctx2)

        obj = PdfBuilder(
            name    = f'{qsq_name}/{bins.dir_path}/{model}',
            label   = 'Smeared' if smear else 'Unsmeared',
            comp    = comp,
            trigger = trigger,
            qsq     = qsq)

        obj.get_model(
            obs_ext= obs,
            use_kde= use_kde,
            mode   = mode)
# ----------------------------------------------------------------------
