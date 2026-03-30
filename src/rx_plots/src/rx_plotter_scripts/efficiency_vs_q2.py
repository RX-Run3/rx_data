'''
This script is meant to make plots of the efficiency in MC
in function of the true q2
'''
import os
import random
import argparse
import numpy
import mplhep
import matplotlib.pyplot   as plt
import pandas              as pnd

from typing       import Final
from hist         import Hist
from hist.axis    import Regular
from ROOT         import RDF # type: ignore
from omegaconf    import DictConfig
from dmu          import LogStore
from dmu.generic  import utilities as gut
from rx_common    import Cuts, Qsq, Component, Trigger, QsqDef
from rx_data      import RDFGetter
from rx_selection import selection as sel

log=LogStore.add_logger('rx_plots:efficiency_vs_q2')
XVAR : Final[str  ] = 'q2_true'
RAN  : Final[float] = random.random()
# ----------------------
class Data:
    '''
    Class meant to be used to share attributes
    '''
    cfg     : DictConfig
    channel : str|None        = None
    analysis: str|None        = None

    mplhep.style.use('LHCb2')

    ana_dir  = os.environ['ANADIR']
# ----------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='Script needed to plot efficiency vs true q2')
    parser.add_argument('-c', '--channel' , type=str, help='Channel' , choices=['ee', 'mm'])
    parser.add_argument('-a', '--analysis', type=str, help='Analysis', choices=['rk', 'rkst'])
    args = parser.parse_args()

    Data.channel  = args.channel
    Data.analysis = args.analysis
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
def _get_data(q2bin : Qsq) -> pnd.DataFrame:
    '''
    Parameters
    -------------
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

    [sample, trigger_str] = Data.cfg.input[f'{Data.analysis}_{Data.channel}']
    component = Component.from_sample(sample)
    trigger   = Trigger(trigger_str)

    gtr = RDFGetter(
        sample = component, 
        trigger= trigger)
    rdf = gtr.get_rdf(per_file=False)
    rdf = _preselect(rdf = rdf, component = component, trigger = trigger)
    rdf = _add_flags(rdf=rdf, q2bin = q2bin)

    data= rdf.AsNumpy([ qsqdef for qsqdef in QsqDef ] + [XVAR])
    df  = pnd.DataFrame(data)
    df.attrs['total'] = _get_mcdt_q2(sample=component, trigger=trigger)

    return df
# ----------------------
def _get_hist(
    df  : pnd.DataFrame,
    axis: Regular,
    flag: QsqDef | None) -> Hist:
    '''
    Parameters
    -------------
    df  : DataFrame with q2_true column and flags
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
        arr_q2  = df_filt[XVAR].to_numpy()

    arr_q2    = arr_q2 / 1000_000.
    histogram = Hist(axis)
    histogram.fill(arr_q2)

    return histogram
# ----------------------
def _check_none(obj : DictConfig|None, kind : str) -> DictConfig:
    '''
    Parameters
    -------------
    obj : omegaconf dictionary with configuration
    kind: Key that has to exist in config

    Returns
    -------------
    The config if it passes checks
    '''
    if obj is None:
        raise ValueError(f'Config {kind} not found')

    if kind not in obj:
        raise ValueError(f'Cannot find key {kind} in config')

    return obj
# ----------------------
def _add_lines() -> None:
    '''
    Parameters
    -------------
    None

    Returns
    -------------
    None
    '''
    if 'lines' not in Data.cfg:
        log.warning('Not adding lines')
        return

    cfg   = _check_none(obj=Data.cfg, kind='lines')
    for bound in cfg.lines.bounds.values():
        plt.axvline(x=bound, **cfg.lines.styling)
# ----------------------
def _plot_efficiencies(
    df     : pnd.DataFrame,
    qsqdef : QsqDef) -> None:
    '''
    Parameters
    -------------
    df  : Pandas dataframe with: q2_true, pass_all and pass_def/dtf/tru
        with numpy array with q2 from MCDecayTree attached with key `total`
    kind: Type of q2 variable to use for selection

    Returns
    -------------
    Nothing, this should only plot efficiencies
    '''
    cfg       = _check_none(obj=Data.cfg, kind='hist_conf')
    hist_conf = cfg.hist_conf

    axis  = Regular(**hist_conf[XVAR])
    h_all = _get_hist(df=df, axis=axis, flag= qsqdef)
    h_den = _get_hist(df=df, axis=axis, flag= None  )

    h_eff_tot = RAN * h_all / h_den

    h_eff_tot.plot(histtype='step', label=qsqdef.latex)
# ----------------------
def _get_out_path(q2bin : str) -> str:
    '''
    Parameters
    -------------
    var  : Name of variable in function of which efficiency is measured
    q2bin: E.g. central

    Returns
    -------------
    Path to PNG file where plot should go
    '''
    out_dir = f'{Data.ana_dir}/plots/checks/efficiency_vs_q2/{Data.analysis}_{Data.channel}/{q2bin}'
    os.makedirs(out_dir, exist_ok=True)

    out_path = f'{out_dir}/{XVAR}.png'

    return out_path
# ----------------------
def _plot(
    df   : pnd.DataFrame,
    q2bin: Qsq) -> None:
    '''
    Parameters
    -------------
    df   : Pandas dataframe with q2 and MVA scores
    q2bin: E.g. central, high
    '''
    plt.figure(figsize = Data.cfg.figure.size)
    for qsqdef in QsqDef:
        _plot_efficiencies(df=df, qsqdef = qsqdef)

    out_path = _get_out_path(q2bin=q2bin)

    _add_lines()

    cfg = _check_none(obj=Data.cfg, kind='input')
    [sample, trigger] = cfg.input[f'{Data.analysis}_{Data.channel}']

    component = Component.from_sample(sample)

    plt.title(f'{component.latex}; {trigger}')
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
def main(cfg : DictConfig | None = None) -> None:
    '''
    Parameters
    ------------------
    cfg: Config storing settings if used as module instead of script 
    '''
    if cfg is None:
        _parse_args()
    else:
        Data.analysis = cfg.analysis
        Data.channel  = cfg.channel

    _set_logs()
    log.debug('Loading configuration')
    Data.cfg = gut.load_conf(package='rx_plotter_data', fpath='efficiency/vs_q2.yaml')

    for q2bin in Qsq: 
        if q2bin in {Qsq.none, Qsq.all}:
            continue

        df = _get_data(q2bin = q2bin)
        _plot(df = df, q2bin= q2bin)
# ----------------------
if __name__ == '__main__':
    main()
