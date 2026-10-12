'''
This script is meant to be the entry point for all the functionalities
provided by this project
'''
# ruff: noqa: PLC0415

import os
import typer
import pandas as pnd

from contextlib import ExitStack
from enum       import StrEnum, auto
from typing     import Final
from rx_common  import Trigger, Qsq
from dmu        import LogLevels, LogStore
from dmu.stats  import zfit
from pathlib    import Path
from fitter     import YieldGrid
from fitter     import FitSummary

app = typer.Typer(
    help            = __doc__,
    context_settings= {"help_option_names": ["-h", "--help"]})
log = LogStore.add_logger('rx_fitter:cli')

_ANADIR : Final[Path] = Path(os.environ['ANADIR'])
# ----------------------
class FitKind(StrEnum):
    rare = auto()
    reso = auto()
# ----------------------
def __save_grid_plot(
    grid : YieldGrid, 
    kind : str,
    name : str):
    '''
    Parameters
    -----------------
    grid: Object holding yields in grid
    name: Name of file where grid plot will be saved
    '''
    from rx_plotter import GridPlotter

    out_path = _ANADIR / f'yields/rare/{kind}/{name}.png'

    ptr  = GridPlotter(grid = grid)
    ptr.plot(path = out_path, randomize = False)

    out_path = out_path.with_suffix('.json')
    grid.to_json(path = out_path)
# ----------------------
def __get_signal_grid(
    trig : Trigger,
    q2bin: Qsq,
    name : str,
    proc : int, 
    cmb  : float, 
    prc  : float) -> tuple[YieldGrid, Path]: 
    '''
    Returns
    ---------------
    Tuple with yield grid and path to directory where outputs are saved
    '''
    from fitter     import YieldCalculator
    from rx_common  import Cut, Cuts
    from rx_common  import WorkingPoint
    from ROOT       import EnableImplicitMT

    if proc > 1:
        log.info(f'Using {proc} threads')
        EnableImplicitMT(proc)

    cmb_obj = Cut(cut = Cuts.cmb, val = cmb, var = 'mva_cmb')
    prc_obj = Cut(cut = Cuts.prc, val = prc, var = 'mva_prc')
    wpt     = WorkingPoint(root = [cmb_obj, prc_obj])

    cal = YieldCalculator(
        name    = name,
        wp      = wpt,
        q2bin   = q2bin, # for tests, should be rare otherwise
        trigger = trig)

    grid = cal.calculate()

    return grid, cal.path
# ----------------------
@app.command()
def tabulate_scales(
    ncores : int = typer.Option(1, '--ncores', '-n', help='Number of cores')) -> None: # noqa: B008
    '''
    Makes table of signal over background scale factors
    '''
    from ROOT      import EnableImplicitMT # type: ignore
    from fitter    import ScalesTabulator
    from fitter    import ScalesTabulatorConf

    if ncores > 1:
        log.info(f'Using {ncores} cores')
        EnableImplicitMT(ncores)

    cfg = ScalesTabulatorConf.load()
    ptr = ScalesTabulator(cfg = cfg)
    ptr.run()
# ----------------------
@app.command()
def tabulate_mc_stats(
    cache: bool    = typer.Option(True, '--cache/--no-cache', '-c', help='If used will re-use cached file '), # noqa: B008 
    trig : Trigger = typer.Option(... , '--trigger', '-t', help='Name trigger'                    ),          # noqa: B008 
    name : str     = typer.Option(... , '--name'   , '-n', help='Name of fit group')              ) -> None:  # noqa: B008
    '''
    Makes latex table with cutflow for low statistics samples that were dropped from fits
    '''
    from dmu.pdataframe import utilities as put
    from fitter         import DatasetSummary
    from rx_common      import Cuts

    cache_path = Path('/tmp/data_summary.parquet')
    if cache and cache_path.exists():
        log.info(f'Picking cached dataframe from: {cache_path}')
        df = pnd.read_parquet(cache_path)
    else:
        log.info('Creating dataframe')
        dsm = DatasetSummary(name = name, trigger = trig)
        df  = dsm.get_df()

    df.to_parquet(cache_path)
    df = df.query('Sample != \"Data\"')
    df = df.query('Block  == 1')
    for _, df_brem in df.groupby(by = 'Brem'):
        for sample, df_sample in df_brem.groupby(by = 'Sample'):
            for q2bin, df_q2bin in df_sample.groupby(by = 'q2bin'):
                df_q2bin.drop(columns = ['Block', 'Brem', 'Sample', 'q2bin'], inplace = True)

                cut_has_block = df_q2bin['cut'].str.contains('block')
                df_filt = df_q2bin[~cut_has_block]

                cut_has_brem  = df_filt['cut'].str.contains('brem')
                df_filt = df_filt[~cut_has_brem]

                cols = list(df_filt.columns)
                cols[0], cols[1] = cols[1], cols[0]
                df_filt = df_filt[cols]
                df_filt = df_filt.rename(columns={df.columns[1]: 'Cut'})
                df_filt['Cut'] = df_filt['Cut'].str.strip()

                path    = _ANADIR / 'tables/dropped_stats' / f'{sample}_{q2bin}.tex'
                path.parent.mkdir(parents = True, exist_ok = True)

                cuts           = df_filt['Cut'].to_list()
                cut_map        = { cut : Cuts(cut).latex for cut in cuts }
                df_filt['Cut'] = df_filt['Cut'].replace(cut_map)

                put.df_to_tex(
                    df      = df_filt, 
                    path    = path)
# ----------------------
@app.command()
def fit_summary(
    kind    : FitKind = typer.Option(...           , '--kind'   , '-k', help='E.g. rare or reso'), # noqa: B008
    name    : str     = typer.Option(...           , '--name'   , '-n', help='Name of fits, e.g. mid_window'),
    log_lvl : int     = typer.Option(LogLevels.info, '--log_lvl', '-l', help='Logging level'))-> None:
    '''
    This will create a fit summary for a given fit
    '''
    from fitter.fit_summary import FitSummarizer

    smr = FitSummarizer(name = name, kind = kind)
    smr.get_summary(
        out_name     = 'fit_summary.json',
        force_update = True)

    LogStore.set_level('rx_fitter:fit_summary', log_lvl)
# ----------------------
@app.command()
def make_dummy_plot(
    text   : str = typer.Option('Placeholder', '--text'  , '-t', help='Text that will go in plot'),
    source : str = typer.Option('Placeholder', '--source', '-s', help='Path to source of file to be copied'),
    path   : Path= typer.Option(...          , '--path'  , '-p', help='Path to PNG file to be made')) -> None: # noqa: B008
    '''
    This will check if a plot exists and if not, will create a placeholder
    '''
    import matplotlib.pyplot as plt

    if path.exists():
        log.debug(f'Path found: {path}')
        return

    path.parent.mkdir(parents = True, exist_ok=True)

    log.debug(f'Path not found, making it: {path}')
    plt.figure(figsize=(15, 10))
    plt.text(0.5, 0.5, text,
        fontsize = 72,
        color    = 'red',
        ha       = 'center',
        va       = 'center',
        weight   = 'bold')
    plt.text(0.5, 0.1, source,
        fontsize = 12,
        color    = 'blue',
        ha       = 'center',
        va       = 'center',
        weight   = 'bold')
    plt.axis('off')
    plt.savefig(path)
    plt.close('all')
# ----------------------
@app.command()
def wp_translator(
    wp   : str = typer.Option(..., '--wp', '-w', help='Working point, e.g. 300')) -> None:
    '''
    This will print the signal probability (i.e. MVA working point) given a string
    '''
    from rx_common import MVAWp # noqa 

    val = MVAWp.from_str(val = wp)

    print(val)
# ----------------------
@app.command()
def prefit_postfit(
    update : bool = typer.Option(False, '--update', '-u', help='Will remake all plots')) -> None:
    '''
    Makes prefit and postfit plots of fit parameters
    '''
    from fitter    import plot_prefit_postfit # noqa: PLC0415 

    plot_prefit_postfit(update = update)
# ----------------------
@app.command()
def calculate_sweights(
    nll_path : Path = typer.Option(..., '--file', '-f', help='Full path to file with NLL')) -> None: # noqa: B008
    '''
    Makes prefit and postfit plots of fit parameters
    '''
    import matplotlib.pyplot as plt
    import mplhep

    from dmu.stats import utilities as sut
    from dmu.stats import Function, splot

    nll    = sut.load_nll(path = nll_path)
    pdf    = nll.model[0]
    dat    = nll.data[0]
    masses = dat.to_numpy().flatten()

    if not isinstance(pdf, zfit.pdf.SumPDF):
        raise ValueError('Fit model is not a SumPDF')

    sweights  = splot.compute_sweights(
        model = pdf, 
        x     = masses)

    plt.style.use(mplhep.style.LHCb2) # type: ignore

    for par, weights in sweights.items():
        swt_path = nll_path.parent / f'swt_{par.name}.json'

        fun   = Function(
            x = masses,
            y = weights)
        fun.save(path = swt_path, plot = True)
# ----------------------
# Yield grids
# ----------------------
@app.command()
def expected_signal(
    proc    : int     = typer.Option(1  , '--proc'   , '-p', help='Number of threads to process with'),
    name    : str     = typer.Option(..., '--name'   , '-n', help='Name of config file'),
    cmb     : float   = typer.Option(..., '--cmb'    , '-c', help='Working point for combinatorial MVA'),
    prc     : float   = typer.Option(..., '--prc'    , '-p', help='Working point for part-reco MVA'),
    trigger : Trigger = typer.Option(..., '--trigger', '-t', help='E.g. rk_ee_os'),          # noqa: B008
    q2bin   : Qsq     = typer.Option(..., '--q2bin'  , '-q', help='E.g. central' )) -> None: # noqa: B008
    '''
    Calculates grid of signal expected yields in grid of MVA classifiers working points
    '''
    from rx_plotter import GridPlotter

    grid, path = __get_signal_grid(proc = proc, trig = trigger, q2bin = q2bin, cmb = cmb, prc = prc, name = name)
    ptr        = GridPlotter(grid = grid)

    ptr.plot(path = path / 'yields.png', randomize = True)
# ----------------------
@app.command()
def fitted_background(
    name    : str     = typer.Option(..., '--name'   , '-n', help='Name of config file'),
    trigger : Trigger = typer.Option(..., '--trigger', '-t', help='E.g. rk_ee_os'),          # noqa: B008
    q2bin   : Qsq     = typer.Option(..., '--q2bin'  , '-q', help='E.g. central' )) -> None: # noqa: B008
    '''
    Plots background yields
    '''
    from rx_common  import Component

    path    = _ANADIR / f'fits/data/{name}/fit_summary.json'
    summary = FitSummary.from_json(path = path) 
    summary = summary.query(name = 'component', value = Component.data_24)
    summary = summary.query(name = 'project'  , value = trigger.project) 
    summary = summary.query(name = 'q2bin'    , value = q2bin)

    variables = summary.get_fitted_yields(exclude = trigger.rare_signal)
    log.info('Building grid from yields:')
    for var in variables:
        log.info(var)

    grid : YieldGrid | None = None 
    for variable in variables:
        tmp = summary.make_grid(var = variable, fall_back = 0.)
        __save_grid_plot(
            grid = tmp, 
            kind = 'fitted_background',
            name = f'{trigger}_{q2bin}_{variable}')

        if grid is None:
            grid  = tmp
        else:
            grid += tmp 

    if grid is None:
        raise ValueError('Missing yields grid')

    __save_grid_plot(
        grid = grid, 
        kind = 'fitted_background',
        name = f'{trigger}_{q2bin}_total')
# ----------------------
@app.command()
def significance(
    proc    : int     = typer.Option(1  , '--proc'   , '-p', help='Number of threads to process with'),
    grid    : str     = typer.Option(..., '--grid'   , '-g', help='Name of config file with grid'),
    fits    : str     = typer.Option(..., '--fits'   , '-f', help='Name of fits, e.g. rare_full_scan'),
    cmb     : float   = typer.Option(..., '--cmb'    , '-c', help='Working point for combinatorial MVA'),
    prc     : float   = typer.Option(..., '--prc'    , '-p', help='Working point for part-reco MVA'),
    trigger : Trigger = typer.Option(..., '--trigger', '-t', help='E.g. rk_ee_os'),          # noqa: B008
    q2bin   : Qsq     = typer.Option(..., '--q2bin'  , '-q', help='E.g. central' )) -> None: # noqa: B008
    '''
    Calculates signal significances in grid of MVA classifiers working points
    '''
    from rx_plotter import GridPlotter
    from rx_common  import Component
    from fitter     import Yield

    path    = _ANADIR / f'fits/data/{fits}/fit_summary.json'
    summary = FitSummary.from_json(path = path) 
    summary = summary.query(name = 'component', value = Component.data_24)
    summary = summary.query(name = 'project'  , value = trigger.project) 
    summary = summary.query(name = 'q2bin'    , value = q2bin)

    variables = summary.get_fitted_yields(exclude = trigger.rare_signal)
    log.info('Building grid from yields:')
    for var in variables:
        log.info(var)

    grid_bkg : YieldGrid | None = None 
    for variable in variables:
        tmp = summary.make_grid(var = variable, fall_back = 0.)

        if grid_bkg is None:
            grid_bkg  = tmp
        else:
            grid_bkg += tmp 

    if grid_bkg is None:
        raise ValueError('background yield is None')

    grid_bkg       = grid_bkg.patch()
    grid_sig, path = __get_signal_grid(proc = proc, trig = trigger, q2bin = q2bin, cmb = cmb, prc = prc, name = grid)

    ctx_1 = YieldGrid.allow_unmatched()
    ctx_2 = Yield.allow_nan()
    with ExitStack() as stack:
        stack.enter_context(ctx_1)
        stack.enter_context(ctx_2)

        grid_sgn = grid_sig / (grid_sig + grid_bkg).sqrt

    grids = {'signal' : grid_sig, 'background' : grid_bkg, 'significance' : grid_sgn}

    for name, this_grid in grids.items():
        ptr = GridPlotter(grid = this_grid)
        ptr.plot(path = path / f'{name}.png', randomize = False)
# ----------------------
@app.command()
def expected_background(
    name    : str     = typer.Option(..., '--name'   , '-n', help='Name of config file'),
    cmb     : float   = typer.Option(..., '--cmb'    , '-c', help='Working point for combinatorial MVA'),
    prc     : float   = typer.Option(..., '--prc'    , '-p', help='Working point for part-reco MVA'),
    trigger : Trigger = typer.Option(..., '--trigger', '-t', help='E.g. rk_ee_os'),          # noqa: B008
    q2bin   : Qsq     = typer.Option(..., '--q2bin'  , '-q', help='E.g. central' )) -> None: # noqa: B008
    '''
    Plots background yields
    '''
    from rx_common  import Component
    from fitter     import YieldCalculator, Yield
    from rx_common  import Cut, Cuts
    from rx_common  import WorkingPoint

    cmb_obj = Cut(cut = Cuts.cmb, val = cmb, var = 'mva_cmb')
    prc_obj = Cut(cut = Cuts.prc, val = prc, var = 'mva_prc')
    wpt     = WorkingPoint(root = [cmb_obj, prc_obj])

    cal         = YieldCalculator(
        name    = 'full_scan',
        wp      = wpt,
        q2bin   = q2bin, # for tests, should be rare otherwise
        trigger = trigger)

    grid_sig = cal.calculate()
    __save_grid_plot(
        grid = grid_sig, 
        kind = 'expected_background',
        name = f'{trigger}_{q2bin}_sig')

    path    = _ANADIR / f'fits/data/{name}/fit_summary.json'

    summary = FitSummary.from_json(path = path)
    summary = summary.query(name = 'component', value = Component.data_24)
    summary = summary.query(name = 'project'  , value = trigger.project  ) 
    summary = summary.query(name = 'q2bin'    , value = q2bin            )

    grid_all = summary.make_grid(var = 'yld_all', fall_back = 0)
    __save_grid_plot(
        grid = grid_all, 
        kind = 'expected_background',
        name = f'{trigger}_{q2bin}_all')

    with Yield.allow_nan():
        grid_bkg = grid_all - grid_sig

    __save_grid_plot(
        grid = grid_bkg, 
        kind = 'expected_background',
        name = f'{trigger}_{q2bin}_bkg')
# ----------------------
if __name__ == '__main__':
    app()
