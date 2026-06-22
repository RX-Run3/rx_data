'''
This script is meant to be the entry point for all the functionalities
provided by this project
'''

import os
import tqdm
import typer
import mplhep
import pandas              as pnd
import matplotlib.pyplot   as plt

from pathlib               import Path
from dmu                   import LogStore
from rx_data.rdf_getter    import RDFGetter
from rx_common             import Trigger, Qsq, Component
from rx_common             import info
from rx_plotter.refitting  import plot      as refitting_plot
from rx_selection          import selection as sel

plt.style.use(mplhep.style.LHCb2)
app = typer.Typer(
    help            = __doc__,
    context_settings= {"help_option_names": ["-h", "--help"]})
log = LogStore.add_logger('rx_plots:cli')
# ----------------------
@app.command()
def refitting(
    max_evt : int     = typer.Option(-1 , '--max_evt', '-m', help='Maximum number of entries'),
    log_lvl : int     = typer.Option(20 , '--log_lvl', '-l', help='Logging level'),
    nthread : int     = typer.Option(4  , '--nthread', '-n', help='Number of threads'),
    project : str     = typer.Option(..., '--project', '-p', help='E.g. rk, rkst'),
    qsq     : Qsq     = typer.Option(..., '--qsq'    , '-q', help='q2 bin'),
    trigger : Trigger = typer.Option(..., '--trigger', '-t')) -> None:
    '''
    This will compare refitted and non-refitted data
    '''
    if project not in ['rk', 'rkst']:
        raise ValueError(f'Invalid project: {project}')

    LogStore.set_level('rx_plots:refitting', log_lvl)

    if max_evt > 0:
        log.warning(f'Running over {max_evt} entries')
        with RDFGetter.max_entries(value = max_evt):
            refitting_plot(project=project, qsq=qsq, trigger=trigger)
    else:
        log.info(f'Running over full dataset with {nthread} threads')
        refitting_plot(project=project, qsq=qsq, trigger=trigger)
# ----------------------
@app.command()
def control_region(
    chan : str = typer.Option(... , '--chan', '-c', help='E.g. EE'      ),
    kind : str = typer.Option(... , '--kind', '-k', help='E.g, OS, SS, EXT'),
    mass : str = typer.Option(... , '--mass', '-m', help='E.g, B_Mass_hdkk, B_Mass_hdpipi'),
    proj : str = typer.Option(... , '--proj', '-p', help='E.g. RK'      ),
    qsq  : str = typer.Option(... , '--qsq' , '-q', help='E.g. central' )) -> None:
    '''
    This can be used to plot control regions for data
    '''
    trig   = info.get_trigger(project = proj, channel = chan, kind = kind)
    sample = 'DATA_24*'

    gtr = RDFGetter(sample = Sample(sample), trigger = Trigger(trig))
    rdf = gtr.get_rdf(per_file = False)

    if   mass == 'B_Mass_hdpipi':
        tg_cut = 'L1_PROBNN_K < 0.1 && L1_PROBNN_K < 0.1'
    elif mass == 'B_Mass_hdkk':
        tg_cut = 'L1_PROBNN_K > 0.1 && L1_PROBNN_K > 0.1'
    else:
        raise ValueError(f'Invalid mass: {mass}')

    l1_cut = 'L1_ProbNNe < 0.2 || L1_PIDe < 3.0'
    l2_cut = 'L2_ProbNNe < 0.2 || L2_PIDe < 3.0'
    mv_cut = '(mva_cmb > 0.50) && (mva_prc > 0.50)'

    with sel.custom_selection(d_sel = {'pid_l' : f'({l1_cut}) && ({l2_cut}) && ({tg_cut})', 'bdt' : mv_cut}):
        rdf = sel.apply_full_selection(
            rdf     = rdf, 
            q2bin   = qsq, 
            process = sample, 
            out_path= Path('./cutflow'),
            trigger = trig)

    arr_mass = rdf.AsNumpy([mass])[mass]

    lmass = {'B_Mass_hdpipi' : r'$M_{e\to\pi}$', 'B_Mass_hdkk' : r'$M_{e\to K}$'}[mass]
    label = {'RK' : f'{lmass}$(B^+)$[MeV]' , 'RKst' : f'{lmass}$(B^0)$[MeV]'}[proj]

    title = f'{l1_cut}\n {l2_cut}\n {mv_cut}\n {tg_cut}' 
    plt.hist(arr_mass, bins = 100, range=(5000, 5500), label = 'Control region', color='blue', alpha=0.5)
    plt.axvline(x=5280, color='red', linestyle=':', label = 'PDG')
    plt.title(title)
    plt.xlabel(label)
    plt.legend()

    name     = f'{chan}_{mass}_{proj}_{qsq}'
    ana_dir  = Path(os.environ['ANADIR'])
    out_path = ana_dir / f'plots/control_region/PID/{name}.png'
    out_path.parent.mkdir(parents = True, exist_ok = True)

    plt.savefig(out_path)
# ----------------------
@app.command()
def block_fraction_vs_q2(
    sample : Sample = typer.Option(..., '--sample' , '-s', help='MC sample, e.g. bpkpee'),
    trigger: Trigger= typer.Option(..., '--trigger', '-t', help='Trigger, e.g. rk_os_ee')) -> None:
    '''
    Used to plot block fraction in MC vs q2 
    '''
    cache_path = Path(f'/tmp/block_fraction_vs_q2/{sample}_{trigger}.json')
    if cache_path.exists():
        log.info(f'Found cached data, loading from: {cache_path}')
        df = pnd.read_json(cache_path)
    else:
        df = _calculate_stats(
            sample     = sample,
            trigger    = trigger,
            cache_path = cache_path)

    _plot_block_fraction_vs_q2(df = df)
# ----------------------
def _plot_block_fraction_vs_q2(df : pnd.DataFrame) -> None:
    '''
    Parameters
    -------------
    df: Pandas dataframe with block, q2bin, true and reco yields
    '''
    df['Efficiency'] = df['reco'] / df['true']

    ax = None
    for q2bin, df_q2 in df.groupby('q2bin'):
        df_q2['eff_frac'] = df_q2['Efficiency'] / df_q2['Efficiency'].sum()

        label = Qsq(q2bin).latex
        ax    = df_q2.plot(x='block', y='eff_frac', label=label, ax = ax)

    plt.ylim(bottom=0.0, top=0.20)
    plt.ylabel(r'$\varepsilon^{block}(q^2)/\varepsilon(q^2)$')
    plt.show()
# ----------------------
def _calculate_stats(
    sample     : Sample,
    trigger    : Trigger,
    cache_path : Path) -> pnd.DataFrame:
    '''
    Parameters
    -------------
    cache_path: Path used to store as JSON, the dataframe
    sample    : MC Sample to study
    trigger   : Trigger under which to study it

    Returns
    -------------
    Pandas dataframe with yields per q2bin, block and for true and reco columns
    '''
    gtr_true = RDFGetter(sample = sample, trigger = trigger, tree = 'MCDecayTree')
    rdf_true = gtr_true.get_rdf(per_file = False)

    gtr_reco = RDFGetter(sample = sample, trigger = trigger, tree = 'DecayTree')
    rdf_reco = gtr_reco.get_rdf(per_file = False)

    with sel.custom_selection(d_sel = {'q2' : '(1)'}):
        rdf_reco = sel.apply_full_selection(
            rdf     = rdf_reco, 
            process = sample,
            q2bin   = Qsq.central,
            trigger = trigger)

    l_data : list[dict] = [] 
    entries = [ (block, q2bin) for block in range(1, 9) for q2bin in Qsq ]

    true_yield = rdf_true.Count()
    for block, q2bin in entries:
        if q2bin == Qsq.all:
            continue

        q2_cut     = sel.get_q2_cut(q2bin = q2bin)
        rdf_sel    = rdf_reco
        rdf_sel    = rdf_sel.Filter(f'block == {block}', 'block')
        rdf_sel    = rdf_sel.Filter(             q2_cut, 'q2bin')
        reco_yield = rdf_sel.Count()

        data = {
            'block': block,
            'q2bin': q2bin,
            'true' : true_yield,
            'reco' : reco_yield,
        }

        l_data.append(data)

    data = []
    for item in tqdm.tqdm(l_data, ascii=' -'):
        data.append({
            'block': item['block'],
            'q2bin': item['q2bin'],
            'true' : item['true' ].GetValue(),
            'reco' : item['reco' ].GetValue()
        })

    df = pnd.DataFrame(data)

    log.info(f'Caching to: {cache_path}')

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_json(cache_path, indent=2)

    return df
# ----------------------
if __name__ == '__main__':
    app()
