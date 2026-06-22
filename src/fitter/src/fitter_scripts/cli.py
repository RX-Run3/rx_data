'''
This script is meant to be the entry point for all the functionalities
provided by this project
'''

import typer
import mplhep
import matplotlib.pyplot as plt

from hepstats    import splot
from dmu         import LogLevels, LogStore
from pathlib     import Path
from rx_common   import Component
from dmu.stats   import utilities as sut
from dmu.stats   import Function

app = typer.Typer(
    help            = __doc__,
    context_settings= {"help_option_names": ["-h", "--help"]})
log = LogStore.add_logger('rx_fitter:cli')
# ----------------------
@app.command()
def fit_summary(
    name    : str       = typer.Option(...           , '--name'   , '-n', help='Name of fits, e.g. mid_window'),
    signal  : Component = typer.Option(...           , '--signal' , '-s', help='Name of signal, e.g. bpkpee'), # noqa: B008
    log_lvl : int       = typer.Option(LogLevels.info, '--log_lvl', '-l', help='Logging level'))-> None:
    '''
    This will create a fit summary for a given fit
    '''
    from fitter    import FitSummary # noqa: PLC0415 

    smr = FitSummary(
        data   = Component.data_24,
        signal = signal,
        name   = name)
    smr.get_df()

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
    from fitter import MVAWp # noqa 

    val = MVAWp.from_label(val = wp)

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
    nll    = sut.load_nll(path = nll_path)
    pdf    = nll.model[0]
    dat    = nll.data[0]
    masses = dat.to_numpy().flatten()

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
if __name__ == '__main__':
    app()

