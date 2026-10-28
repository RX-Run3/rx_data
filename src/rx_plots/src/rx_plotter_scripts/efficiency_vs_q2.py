'''
This script is meant to make plots of the efficiency in MC
in function of the true q2
'''
import os
import argparse
import numpy
import mplhep
import matplotlib.pyplot   as plt
import pandas              as pnd
import random

from pathlib      import Path
from typing       import Final
from hist         import Hist
from hist.axis    import Regular
from ROOT         import RDF
from dmu          import LogStore
from dmu.generic  import utilities as gut
from pydantic     import BaseModel
from rx_common    import Qsq, Component, Trigger, QsqDef
from rx_data      import RDFGetter
from rx_selection import selection as sel

log=LogStore.add_logger('rx_plots:efficiency_vs_q2')

random.seed(123)
_RANDOM : Final[float] = random.randint(0, 100)
_ANADIR : Final[Path ] = Path(os.environ['ANADIR'])
mplhep.style.use('LHCb2')
# ----------------------
class StyleConf(BaseModel):
    '''
    Class meant to configure line style
    '''
    color : str
    ls    : str
    lw    : int
# ----------------------
class HistConf(BaseModel):
    '''
    Class with configuration needed to build histogram
    '''
    name  : str 
    bins  : int 
    start : int 
    stop  : int 
    label : str 
# ----------------------
class FigConf(BaseModel):
    '''
    Config used to create figure
    '''
    size : tuple[int,int]
# ----------------------
class PlotConfig(BaseModel):
    '''
    Class meant to represent plotting configuration
    '''
    component : Component
    trigger   : Trigger
    qsqdef    : QsqDef
    hist_conf : dict[QsqDef,HistConf]
    figure    : FigConf
    line_style: StyleConf
    bounds    : dict[Qsq,float]
# ----------------------
def _parse_args() -> PlotConfig:
    parser = argparse.ArgumentParser(description='Script needed to plot efficiency vs true q2')
    parser.add_argument(
        '-c', 
        '--component', 
        type=Component, 
        help='Component')

    parser.add_argument(
        '-t', 
        '--trigger', 
        type=Trigger, 
        help='Trigger')

    args = parser.parse_args()

    data = gut.load_data(package = 'rx_plotter_data', fpath = 'efficiency/vs_q2.yaml')
    return PlotConfig(
        qsqdef    = QsqDef.true,
        component = args.component,
        trigger   = args.trigger,
        **data)
# ----------------------
def _add_flags(
    rdf   : RDF.RNode,
    q2bin : Qsq) -> RDF.RNode:
    '''
    Parameters
    -------------
    rdf   : ROOT dataframe corresponding to a given MC sample
    q2bin : E.g. central

    Returns
    -------------
    DataFrame with columns for different q2 definitions and values
    of 0 or 1 depending on wether the candidate passes the cut or not
    '''
    cut_org = sel.get_q2_cut(q2bin = q2bin)

    log.info(40 * '-')
    log.info(f'{"Cut":<20}{"Expression"}')
    log.info(40 * '-')
    for qsqdef in QsqDef:
        cut_def = cut_org.replace(QsqDef.default.branch_name, qsqdef.branch_name)
        log.info(f'{qsqdef:<20}{cut_def}')
        rdf = rdf.Define(qsqdef, cut_def)

    return rdf
# ----------------------
def _preselect(
    component: Component,
    trigger  : Trigger,
    rdf      : RDF.RNode) -> RDF.RNode:
    '''
    Parameters
    -------------
    rdf    : ROOT dataframe corresponding to a given MC sample
    sample : Component object 
    trigger: HLT2 trigger name

    Returns
    -------------
    DataFrame with full selection but q2 cut
    '''

    d_full_sel = sel.selection(
        q2bin  =Qsq.jpsi, 
        process=component, 
        trigger=trigger)

    for name, cut in d_full_sel.items():
        if name in {'q2', 'mass'}:
            continue
        rdf = rdf.Filter(cut, name)

    return rdf
# ----------------------
def _get_mcdt_q2(sample : Component, trigger : Trigger) -> numpy.ndarray:
    '''
    Parameters
    -------------
    sample: MC sample, e.g. mc_bdksee...
    trigger: HLT2 trigger

    Returns
    -------------
    Numpy array with q2 values from MCDT divided by 1000_000
    '''
    gtr    = RDFGetter(sample=sample, trigger=trigger, tree='MCDecayTree')
    rdf    = gtr.get_rdf(per_file=False)
    arr_q2 = rdf.AsNumpy(['q2'])['q2']

    return arr_q2
# ----------------------
def _get_data(
    cfg   : PlotConfig,
    q2bin : Qsq) -> pnd.DataFrame:
    '''
    Parameters
    -------------
    cfg  : Plotting configuration
    q2bin: Bin for which the data is needed

    Returns
    -------------
    Pandas DataFrame with:
        - True q2 value
        - Flags for this q2 bins signaling when the candidate enters the bin
          and for different q2 definitions
        - Array of true q2 attached as an atribute with key "total"
    '''

    log.debug('Loading data')

    gtr = RDFGetter(
        sample = cfg.component, 
        trigger= cfg.trigger)
    rdf = gtr.get_rdf(per_file=False)
    rdf = _preselect(rdf = rdf, component = cfg.component, trigger = cfg.trigger)
    rdf = _add_flags(rdf=rdf, q2bin = q2bin)

    data= rdf.AsNumpy([ qsqdef for qsqdef in QsqDef ] + [cfg.qsqdef.branch_name])
    df  = pnd.DataFrame(data)
    df.attrs['total'] = _get_mcdt_q2(sample=cfg.component, trigger=cfg.trigger)

    return df
# ----------------------
def _get_hist(
    df  : pnd.DataFrame,
    cfg : PlotConfig,
    axis: Regular,
    flag: QsqDef | None) -> Hist:
    '''
    Parameters
    -------------
    df  : DataFrame with q2_true column and flags
    cfg : Plotting configuration
    axis: Hist's X axis, needed to make histogram
    var : q2 name, for numerator histogram, q2 or q2_true
    flag: Either None, or q2 definition 
          Needed to control what histogram is made
          If None, will use MCDT q2 values

    Returns
    -------------
    Histogram with q2 distribution
    '''
    if flag is None:
        arr_q2  = df.attrs['total']
    else:
        df_filt = df.query(f'{flag} == 1')
        arr_q2  = df_filt[cfg.qsqdef.branch_name].to_numpy()

    arr_q2    = arr_q2 / 1000_000.
    histogram = Hist(axis)
    histogram.fill(arr_q2)

    return histogram
# ----------------------
def _plot_efficiencies(
    df     : pnd.DataFrame,
    cfg    : PlotConfig,
    qsqdef : QsqDef) -> None:
    '''
    Parameters
    -------------
    df  : Pandas dataframe with: q2_true, pass_all and pass_def/dtf/tru
        with numpy array with q2 from MCDecayTree attached with key `total`
    cfg : Plotting configuration
    kind: Type of q2 variable to use for selection
    '''
    hist_conf = cfg.hist_conf[cfg.qsqdef]
    axis  = Regular(**hist_conf.model_dump())
    h_all = _get_hist(df=df, axis=axis, flag= qsqdef, cfg = cfg)
    h_den = _get_hist(df=df, axis=axis, flag= None  , cfg = cfg)

    h_eff_tot = _RANDOM * h_all / h_den

    if qsqdef == QsqDef.default:
        h_eff_tot.plot(
            alpha   = 0.3,
            histtype= 'fill',
            label   = qsqdef.latex,
            color   = qsqdef.color,
        )
    else:
        h_eff_tot.plot(
            histtype= 'step', 
            label   = qsqdef.latex, 
            color   = qsqdef.color, 
        )
# ----------------------
def _plot(
    df   : pnd.DataFrame,
    cfg  : PlotConfig,
    q2bin: Qsq) -> None:
    '''
    Parameters
    -------------
    df   : Pandas dataframe with q2 and MVA scores
    cfg  : Plotting configuration
    q2bin: E.g. central, high
    '''
    plt.figure(figsize = cfg.figure.size)
    for qsqdef in QsqDef:
        _plot_efficiencies(df=df, qsqdef = qsqdef, cfg = cfg)

    out_path = _ANADIR / f'plots/checks/efficiency_vs_q2/{cfg.component}_{cfg.trigger.value}/{q2bin}/{cfg.qsqdef}.png'
    out_path.parent.mkdir(parents=True, exist_ok=True)

    for bound in cfg.bounds.values():
        plt.axvline(x=bound, **cfg.line_style.model_dump())

    plt.title(f'{cfg.component.latex}; {cfg.trigger}')
    plt.ylabel('A.U.')
    plt.legend()

    log.info(f'Saving to: {out_path}')
    plt.savefig(out_path)
    plt.close()
# ----------------------
def _set_logs() -> None:
    '''
    Will set the log level of different tools
    '''
    LogStore.set_level('rx_selection:truth_matching', 30)
    LogStore.set_level('rx_selection:selection'     , 30)
    LogStore.set_level('rx_data:rdf_getter'         , 30)
# ----------------------
def main(args : dict[str,str] | None = None) -> None:
    '''
    Entry point
    '''
    if args:
        data = gut.load_data(package = 'rx_plotter_data', fpath = 'efficiency/vs_q2.yaml')
        cfg  = PlotConfig(
            component = Component(args['component']),
            trigger   = Trigger(args['trigger'  ]),
            qsqdef    = QsqDef.true,
            **data,
        )
    else:
        cfg = _parse_args()

    _set_logs()
    log.debug('Loading configuration')

    for q2bin in Qsq: 
        if q2bin == Qsq.none:
            continue

        df = _get_data(q2bin = q2bin, cfg = cfg)
        _plot(df = df, q2bin= q2bin, cfg = cfg)
# ----------------------
if __name__ == '__main__':
    main()
