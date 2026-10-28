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

from ROOT         import EnableImplicitMT
from pathlib      import Path
from dmu          import LogStore
from dmu.generic  import utilities as gut
from rx_data      import RDFGetter
from rx_common    import Channel, Component, Cuts, Project, Trigger, Qsq
from rx_plotter   import CandidateRebuild
from rx_plotter   import CandidateRebuildConf
from rx_plotter   import refitting_plot
from rx_selection import selection as sel
from rx_plotter   import BremRecovery
from rx_plotter   import plot_luminosity
from rx_plotter   import CopyPlots

plt.style.use(mplhep.style.LHCb2)
_ANADIR = Path(os.environ['ANADIR'])
app     = typer.Typer(
    help            = __doc__,
    context_settings= {"help_option_names": ["-h", "--help"]})
log = LogStore.add_logger('rx_plots:cli')
# ----------------------
@app.command()
def sumarize_brem_recovery(
    trigger   : Trigger   = typer.Option(..., '--trigger'  , '-t', help='Hlt2 trigger'     ),          # noqa: B008
    component : Component = typer.Option(..., '--component', '-c', help='MC or data sample')) -> None: # noqa: B008
    '''
    This will create summary plots for custom brem recovery
    '''
    path = _ANADIR / f'plots/comparison/resolution/{component}/{trigger.value}'
    brc  = BremRecovery()
    brc.resolution(path = path)
# ----------------------
@app.command()
def refitting(
    max_evt : int     = typer.Option(-1 , '--max_evt', '-m', help='Maximum number of entries'),
    log_lvl : int     = typer.Option(20 , '--log_lvl', '-l', help='Logging level'),
    nthread : int     = typer.Option(4  , '--nthread', '-n', help='Number of threads'),
    project : str     = typer.Option(..., '--project', '-p', help='E.g. rk, rkst'),
    qsq     : Qsq     = typer.Option(..., '--qsq'    , '-q', help='q2 bin'), # noqa: B008
    trigger : Trigger = typer.Option(..., '--trigger', '-t')) -> None:       # noqa: B008
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
    mass : str     = typer.Option(... , '--mass', '-m', help='E.g, B_Mass_hdkk, B_Mass_hdpipi'),
    trig : Trigger = typer.Option(... , '--trig', '-t', help='E.g. rk_ee_os'      ),          # noqa: B008
    qsq  : Qsq     = typer.Option(... , '--qsq' , '-q', help='E.g. central' )) -> None: # noqa: B008
    '''
    This can be used to plot control regions for data
    '''
    gtr = RDFGetter(sample = Component.data_24, trigger = trig)
    rdf = gtr.get_rdf(per_file = False)

    if   mass == 'B_Mass_hdpipi':
        tg_cut = 'L1_PROBNN_K < 0.1 && L1_PROBNN_K < 0.1'
    elif mass == 'B_Mass_hdkk':
        tg_cut = 'L1_PROBNN_K > 0.1 && L1_PROBNN_K > 0.1'
    else:
        raise ValueError(f'Invalid mass: {mass}')

    l1_cut = 'L1_ProbNNe < 0.2 || L1_PIDe < 3.0'
    l2_cut = 'L2_ProbNNe < 0.2 || L2_PIDe < 3.0'

    selection : dict[Cuts, str] = {
        Cuts.pid_l : f'({l1_cut}) && ({l2_cut}) && ({tg_cut})', 
        Cuts.cmb   : 'mva_cmb > 0.5',
        Cuts.prc   : 'mva_prc > 0.5',
    }

    with sel.custom_selection(d_sel = selection):
        rdf = sel.apply_full_selection(
            rdf     = rdf, 
            q2bin   = qsq, 
            process = Component.data_24, 
            out_path= Path('./cutflow'),
            trigger = trig)

    arr_mass = rdf.AsNumpy([mass])[mass]

    lmass = {'B_Mass_hdpipi' : r'$M_{e\to\pi}$', 'B_Mass_hdkk' : r'$M_{e\to K}$'}[mass]
    label = {'RK' : f'{lmass}$(B^+)$[MeV]' , 'RKst' : f'{lmass}$(B^0)$[MeV]'}[trig.project]

    cmb_cut= selection[Cuts.cmb]
    prc_cut= selection[Cuts.prc]
    title  = f'{l1_cut}\n {l2_cut}\n {prc_cut}\n {cmb_cut}\n {tg_cut}' 
    plt.hist(arr_mass, bins = 100, range=(5000, 5500), label = 'Control region', color='blue', alpha=0.5)
    plt.axvline(x=5280, color='red', linestyle=':', label = 'PDG')
    plt.title(title)
    plt.xlabel(label)
    plt.legend()

    name     = f'{trig.channel}_{mass}_{trig.project}_{qsq}'
    ana_dir  = Path(os.environ['ANADIR'])
    out_path = ana_dir / f'plots/control_region/PID/{name}.png'
    out_path.parent.mkdir(parents = True, exist_ok = True)

    plt.savefig(out_path)
# ----------------------
@app.command()
def block_fraction_vs_q2(
    sample : Component = typer.Option(..., '--sample' , '-s', help='MC sample, e.g. bpkpee'),          # noqa: B008
    trigger: Trigger   = typer.Option(..., '--trigger', '-t', help='Trigger, e.g. rk_os_ee')) -> None: # noqa: B008
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
@app.command()
def rebuild_candidates(
    q2bin  : Qsq       = typer.Option(... , '--q2bin'  , '-q', help='q2 bin, e.g. jpsi, needed for selection'), # noqa: B008
    trigger: Trigger   = typer.Option(... , '--trigger', '-t', help='Hlt2 trigger, e.g. rk_ee_os'), # noqa: B008
    sample : Component = typer.Option(... , '--sample' , '-s', help='Sample, e.g. data_24'), # noqa: B008
    ncores : int       = typer.Option(1   , '--ncores' , '-n', help='Number of cores for multithreading'),
    config : str       = typer.Option(... , '--conf'   , '-c', help='Name of config file')):
    '''
    Will make plots of distributions from rebuilt candidates
    '''
    if ncores > 1:
        log.info(f'Using {ncores} cores')
        EnableImplicitMT(ncores)

    data        = gut.load_data(
        package = 'rx_plotter_data', 
        fpath   =f'candidate_rebuild/{config}.yaml')

    data['q2bin'  ] = q2bin
    data['trigger'] = trigger 
    data['sample' ] = sample 

    cfg = CandidateRebuildConf(**data)
    ptr = CandidateRebuild(cfg = cfg)
    ptr.run()
# ----------------------
@app.command()
def luminosity():
    '''
    Will make plots of distributions from rebuilt candidates
    '''
    plot_luminosity()
    out_path = _ANADIR / 'plots/luminosity/luminosity_vs_run.png'
    out_path.parent.mkdir(exist_ok = True, parents = True)

    log.info(f'Saving to: {out_path}')
    plt.savefig(out_path)
# ----------------------
@app.command()
def copy_plots(
    dry_run : bool= typer.Option(False, '--dry_run', '-d', help='If true will skip copying'),
    conf    : str = typer.Option(...  , '--conf'   , '-c', help='Name of config file, e.g. paths')):
    '''
    Will copy plots following the configuration in `rx_plots_data/{conf}.yaml`
    '''
    log.info(f'Copying plots with config: {conf}')
    cpr = CopyPlots.from_config_name(name = conf)
    cpr.run(dry_run = dry_run)
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
    sample     : Component,
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

    with sel.custom_selection(d_sel = {Cuts.q2 : '(1)'}):
        rdf_reco = sel.apply_full_selection(
            rdf     = rdf_reco, 
            process = sample,
            q2bin   = Qsq.central,
            trigger = trigger)

    l_data : list[dict] = [] 
    entries = [ (block, q2bin) for block in range(1, 9) for q2bin in Qsq ]

    true_yield = rdf_true.Count()
    for block, q2bin in entries:
        if q2bin == Qsq.none:
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
