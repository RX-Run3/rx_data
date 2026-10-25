'''
Module in charge of plotting refitted vs non-refitted data
'''

import os

from typing        import Final
from ROOT          import RDF
from pathlib       import Path
from dmu           import LogStore
from dmu.generic   import utilities as gut
from dmu.plotting  import Plotter1D as Plotter
from rx_common     import Qsq, Trigger
from rx_common     import Project
from rx_common     import Component
from rx_data       import RDFGetter
from rx_selection  import selection as sel

log=LogStore.add_logger('rx_plots:refitting')

_DATA : Final[Component] = Component.data_24
# ----------------------
def _get_rdf(
    trigger : Trigger,
    qsq     : Qsq,
    project : Project,
    out_path: Path) -> RDF.RNode:
    '''
    Parameters
    -------------
    channel: Electron or muon
    qsq    : q2 bin
    project: Refitted or not

    Returns
    -------------
    Dataframe after full selection
    '''
    with RDFGetter.project(project = project):
        gtr = RDFGetter(sample = _DATA, trigger = trigger)
        rdf = gtr.get_rdf(per_file = False)

    rdf = sel.apply_full_selection(
        rdf     = rdf,
        process = _DATA,
        q2bin   = qsq,
        trigger = trigger,
        out_path= out_path / project)

    return rdf
# ----------------------
def plot(project : Project, qsq : Qsq, trigger : Trigger):
    '''
    Parameters
    -----------------
    project: E.g. rk_no_refit
    qsq    : q2 bin
    channel: Electron or muon channel
    '''
    ana_dir = Path(os.environ['ANADIR'])
    plt_dir = ana_dir / 'plots/refitting' / trigger / qsq

    rdf_org = _get_rdf(
        trigger  = trigger,
        qsq      = qsq,
        out_path = plt_dir,
        project  = project)

    rdf_rft = _get_rdf(
        trigger  = trigger,
        qsq      = qsq,
        out_path = plt_dir,
        project  = project.main)

    d_rdf   = {'Original' : rdf_org, 'Refitted' : rdf_rft}
    cfg = gut.load_conf(package='rx_plotter_data', fpath = 'refitting/v1.yaml')
    cfg['saving'] = {'plt_dir' : plt_dir}

    ptr = Plotter(d_rdf=d_rdf, cfg=cfg)
    ptr.run()
# ----------------------
