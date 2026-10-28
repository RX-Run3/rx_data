'''
Script used to study effect of different cuts on q2
to get signal in high q2 bin
'''
import os
import argparse
import numpy
import mplhep
import pandas            as pnd
import matplotlib.pyplot as plt

from pathlib               import Path
from typing                import Final, cast
from ROOT                  import RDF
from rx_common             import Component, Cuts, Qsq, Trigger
from rx_data               import RDFGetter
from rx_data.rdf_getter12  import RDFGetter12
from rx_selection          import selection as sel
from dmu                   import LogLevels, LogStore

log=LogStore.add_logger('rx_plots:high_q2cut')
plt.style.use(mplhep.style.LHCb2)

_COMPONENTS : Final[list[Component]] = [
    Component.data_24,
    Component.bpjpsixee,
    Component.bdjpsixee,
    Component.bsjpsixee,
    Component.bpkpee,
    Component.bpkpjpsiee,
    Component.bpkppsi2ee]


_ANADIR : Final[Path] = Path(os.environ['ANADIR'])
# ---------------------------
class Data:
    '''
    Data class
    '''
    plt_dir  : str
    component: Component 
    trigger  : Trigger 
    run      : str

    q2bin   = Qsq.high
    bmass   = 'B_Mass_smr'

    min_q2  = 10
    max_q2  = 24

    cut_min = 14.3
    cut_max = 22.0

    mass_rng= [4500, 6000]

    l_q2var = ['q2_true', 'q2_smr', 'q2_track', 'q2_dtf', 'nbrem', 'B_Mass_smr']
# ---------------------------
def _parse_args():
    parser = argparse.ArgumentParser(description='Used to check efficiency vs q2 for different q2 definitions')
    parser.add_argument('-c', '--component', type=Component, help='MC sample', required=True, choices=_COMPONENTS)
    parser.add_argument('-r', '--run'      , type=      str, help='Run from which to plot', default='run3', choices=['run12', 'run3'])
    args = parser.parse_args()

    Data.component = args.component
    Data.run       = args.run
# ---------------------------
def _initialize():
    plt_dir = f'{_ANADIR}/plots/checks/high_q2cut/{Data.component}/{Data.run}'

    os.makedirs(plt_dir, exist_ok=True)

    if Data.component.is_mc:
        Data.trigger = Trigger.rk_ee_os 
    else:
        Data.trigger = Trigger.rk_ee_ss 

    Data.plt_dir = plt_dir
# ---------------------------
def _get_rdf() -> RDF.RNode:
    if Data.run == 'run3':
        return _get_run3_rdf()

    if Data.run == 'run12':
        return _get_run12_rdf()

    raise ValueError(f'Invalid run: {Data.run}')
# ---------------------------
def _get_run3_rdf() -> RDF.RNode:
    gtr = RDFGetter(
        sample  = Data.component, 
        trigger = Data.trigger)
    rdf = gtr.get_rdf(per_file=False)

    d_sel           = sel.selection(trigger=Data.trigger, q2bin=Data.q2bin, process=Data.component)
    d_sel[Cuts.cmb] = '(1)'
    d_sel[Cuts.prc] = '(1)'
    d_sel[Cuts.q2 ] = '(1)'

    for cut_name, cut_value in d_sel.items():
        rdf = rdf.Filter(cut_value, cut_name)

    if log.getEffectiveLevel() < LogLevels.info:
        rep = rdf.Report()
        rep.Print()

    return rdf
# ---------------------------
def _get_run12_rdf() -> RDF.RNode:
    gtr = RDFGetter12(
            sample = Data.component,
            trigger= Data.trigger,
            dset   = 'all')

    rdf = gtr.get_rdf()
    #rdf = rdf.Filter('BDT_cmb > 0.9 && BDT_prc > 0.8')
    rdf = rdf.Filter('nbrem <= 2')

    return rdf
# ---------------------------
def _reformat_q2(df : pnd.DataFrame) -> pnd.DataFrame:
    l_col = [ col for col in df.columns if col.startswith('q2') ]

    for col in l_col:
        df[col] = df[col] / 1e6

    return df
# ---------------------------
def _rdf_to_df(rdf : RDF.RNode) -> pnd.DataFrame:
    if 'DATA' in Data.component:
        l_q2var = [ var for var in Data.l_q2var if 'true' not in var ]
    else:
        l_q2var = Data.l_q2var

    data = rdf.AsNumpy(l_q2var)
    df   = pnd.DataFrame(data)
    df   = _reformat_q2(df=df)

    return df
# ---------------------------
def _plot(rdf : RDF.RNode) -> None:
    df   = _rdf_to_df(rdf)
    for brem, df_brem in df.groupby('nbrem'):
        brem = cast(str, brem)
        _plot_reco_q2(brem, df=df_brem)
        _plot_true_q2(brem, df=df_brem)

    _plot_reco_q2('all', df)
    _plot_true_q2('all', df)
# ---------------------------
def _plot_eff(arr_val : numpy.ndarray, color : str, ax) -> None:
    sorted_data = numpy.sort(arr_val)
    eff         = 1 - numpy.arange(1, len(arr_val) + 1) / len(arr_val)

    ax.plot(sorted_data, eff, color=color)
# ---------------------------
def _plot_reco_q2(brem : int|str, df : pnd.DataFrame) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(30, 10))

    ax1.hist(df['q2_smr'  ], bins=60, range=[0, Data.max_q2], density=True, label='$q^2$'        , alpha = 0.2, color='blue' )
    ax1.hist(df['q2_dtf'  ], bins=60, range=[0, Data.max_q2], density=True, label='$q^2_{DTF}$'  , alpha = 0.2, color='green')
    ax1.hist(df['q2_track'], bins=60, range=[0, Data.max_q2], density=True, label='$q^2_{track}$', alpha = 0.2, color='red'  )

    df_smr=df[(df.q2_smr   > Data.cut_min) & (df.q2_smr   < Data.cut_max)                             ]
    df_dtf=df[(df.q2_dtf   > Data.cut_min) & (df.q2_dtf   < Data.cut_max) & (df.q2_smr < Data.cut_max)]
    df_trk=df[(df.q2_track > Data.cut_min) & (df.q2_track < Data.cut_max)                             ]

    ax2.hist(df_smr[Data.bmass], bins=60, range=Data.mass_rng, label='$q^2$'        , alpha   =   0.2, color='blue' )
    ax2.hist(df_dtf[Data.bmass], bins=60, range=Data.mass_rng, label='$q^2_{DTF}$'  , histtype='step', color='green')
    ax2.hist(df_trk[Data.bmass], bins=60, range=Data.mass_rng, label='$q^2_{track}$', histtype='step', color='red'  )

    arr_q2smr = df[(df.q2_smr   < Data.cut_max)                             ]['q2_smr'  ].to_numpy()
    arr_q2dtf = df[(df.q2_dtf   < Data.cut_max) & (df.q2_smr < Data.cut_max)]['q2_dtf'  ].to_numpy()
    arr_q2trk = df[(df.q2_track < Data.cut_max)                             ]['q2_track'].to_numpy()

    ax3= ax1.twinx()
    ax1.set_ylim(0, 0.20)
    ax3.set_ylim(0, 0.40)
    ax3.set_xlim(Data.min_q2, Data.max_q2)

    _plot_eff(arr_q2smr, color='blue' , ax=ax3)
    _plot_eff(arr_q2dtf, color='green', ax=ax3)
    _plot_eff(arr_q2trk, color='red'  , ax=ax3)

    ax1.set_xlabel(r'$q^2_{reco}$[GeV$/c^{2}$]')
    ax2.set_xlabel(r'$M(K^+e^+e^-)$')
    ax3.tick_params(axis='y', labelcolor='green')
    ax3.set_ylabel('Efficiency', color='green')

    ax1.legend(loc='upper right', bbox_to_anchor=(0.9, 0.9))
    ax2.legend(loc='upper right', bbox_to_anchor=(0.9, 0.9))

    title = _get_title(brem=brem)

    fig.suptitle(title, fontsize=40)
    ax1.axvline(x=Data.cut_min, c='black', ls=':')
    ax2.axvline(x=5280        , c='black', ls=':')

    if isinstance(brem, float):
        brem = f'{brem:.0f}'

    plot_path = f'{Data.plt_dir}/reco_q2_{brem}.png'
    log.info(f'Saving to: {plot_path}')

    plt.grid()
    plt.savefig(plot_path)
    plt.close()
# ---------------------------
def _plot_true_q2(brem : int|str, df : pnd.DataFrame) -> None:
    if 'DATA' in Data.component:
        return

    df_raw = df
    df_smr = df_raw[ (Data.cut_min < df_raw['q2_smr'  ]) & (df_raw['q2_smr'  ] < Data.cut_max) ]
    df_trk = df_raw[ (Data.cut_min < df_raw['q2_track']) & (df_raw['q2_track'] < Data.cut_max) ]
    df_dtf = df_raw[ (Data.cut_min < df_raw['q2_dtf'  ]) & (df_raw['q2_dtf'  ] < Data.cut_max) ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(30, 10))

    ax1.hist(df_raw['q2_true'], bins=60, range=[0, Data.max_q2], density=False, label=r'No cut'              , alpha   =   0.2, color='blue'  )
    ax1.hist(df_smr['q2_true'], bins=60, range=[0, Data.max_q2], density=False, label=r'Cut on $q^2$'        , histtype='step', color='green' )
    ax1.hist(df_trk['q2_true'], bins=60, range=[0, Data.max_q2], density=False, label=r'Cut on $q^2_{track}$', histtype='step', color='red'   )
    ax1.hist(df_dtf['q2_true'], bins=60, range=[0, Data.max_q2], density=False, label=r'Cut on $q^2_{DTF}$'  , histtype='step', color='orange')

    ax2.hist(df_raw[Data.bmass], bins=60, range=Data.mass_rng, label=r'No cut'              , alpha   =   0.2, color='blue'  )
    ax2.hist(df_smr[Data.bmass], bins=60, range=Data.mass_rng, label=r'Cut on $q^2$'        , histtype='step', color='green' )
    ax2.hist(df_trk[Data.bmass], bins=60, range=Data.mass_rng, label=r'Cut on $q^2_{track}$', histtype='step', color='red'   )
    ax2.hist(df_dtf[Data.bmass], bins=60, range=Data.mass_rng, label=r'Cut on $q^2_{DTF}$'  , histtype='step', color='orange')

    ax1.legend(loc='upper right', bbox_to_anchor=(1.0, 1.0))
    ax2.legend(loc='upper right', bbox_to_anchor=(1.0, 1.0))

    ax1.set_xlabel(r'$q^2_{true}$[GeV$/c^{2}$]')
    ax2.set_xlabel(r'$M(K^+e^+e^-)$')

    title = _get_efficiencies_title(
            df_raw=df_raw,
            df_smr=df_smr,
            df_dtf=df_dtf,
            df_trk=df_trk)

    fig.suptitle(title, fontsize=40)

    if isinstance(brem, float):
        brem = f'{brem:.0f}'

    plot_path = f'{Data.plt_dir}/true_q2_{brem}.png'
    log.info(f'Saving to: {plot_path}')

    plt.grid()
    plt.savefig(plot_path)
    plt.close()
# ---------------------------
def _get_efficiencies_title(
        df_raw : pnd.DataFrame,
        df_smr : pnd.DataFrame,
        df_dtf : pnd.DataFrame,
        df_trk : pnd.DataFrame) -> str:

    tot = len(df_raw)
    smr = len(df_smr)
    dtf = len(df_dtf)
    trk = len(df_trk)

    eff_smr = smr/tot * 100
    eff_dtf = dtf/tot * 100
    eff_trk = trk/tot * 100

    title = (
            f'$\\varepsilon_{{ORG}}={eff_smr:.0f}$%; '
            f'$\\varepsilon_{{DTF}}={eff_dtf:.0f}$%; '
            f'$\\varepsilon_{{TRK}}={eff_trk:.0f}$%'
            )

    return title
# ---------------------------
def _get_title(brem : str|int) -> str:
    return f'Brem = {brem}; {Data.component.latex}'
# ---------------------------
def main(args : dict[str,str] | None = None):
    '''
    Start here
    '''
    if args is None:
        _parse_args()
    else:
        Data.component= Component(args['component'])
        Data.run      = args['run']

    _initialize()

    rdf = _get_rdf()

    _plot(rdf=rdf)
# ---------------------------
if __name__ == '__main__':
    main()
