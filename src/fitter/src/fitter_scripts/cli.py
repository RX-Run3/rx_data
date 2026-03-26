'''
This script is meant to be the entry point for all the functionalities
provided by this project
'''

import typer
import matplotlib.pyplot as plt

from dmu       import LogStore
from pathlib   import Path
from fitter    import FitSummary
from fitter    import MVAConf
from fitter    import plot_prefit_postfit

app = typer.Typer(help=__doc__)
log = LogStore.add_logger('rx_fitter:cli')
# ----------------------
@app.command()
def fit_summary(
    name    : str = typer.Option(..., '--name'   , '-n', help='Name of fits, e.g. mid_window'),
    signal  : str = typer.Option(..., '--signal' , '-s', help='Name of signal, e.g. bpkpee'),
    log_lvl : int = typer.Option(20 , '--log_lvl', '-l', help='Logging level'))-> None:
    '''
    This will create a fit summary for a given fit
    '''
    smr = FitSummary(
        signal = signal,
        name   = name)
    smr.get_df()

    LogStore.set_level('rx_fitter:fit_summary', log_lvl)
# ----------------------
@app.command()
def post_process(
    text : str = typer.Option('Placeholder', '--text', '-t', help='Text that will go in plot'),
    value: str = typer.Option(...          , '--path', '-p', help='Path to PNG file with leading period added')) -> None:
    '''
    This will:

    - Check if a plot exists and if not, will create a placeholder
    - Make a local hidden directory with a dummy output to allow snakemake relase the job

    The input path will be the actual path with a leading period added, e.g. .eos/lhcb/.../file.png
    '''
    if not value.startswith('.'):
        raise ValueError(f'Path is expected to start with a period, found: {value}')

    local_path = Path(value)
    log.info(f'Making: {local_path.parent}')
    local_path.parent.mkdir(parents = True, exist_ok=True)
    log.info(f'Touching: {local_path}')
    local_path.touch()

    value       = '/' + value.lstrip('.')
    remote_path = Path(value)

    if remote_path.exists():
        log.info(f'Path found: {remote_path}')
        return

    remote_path.parent.mkdir(parents=True, exist_ok=True)

    log.info(f'Path not found, making it: {remote_path}')
    plt.figure(figsize=(15, 10))
    plt.text(0.5, 0.5, text,
        fontsize = 72,
        color    = 'red',
        ha       = 'center',
        va       = 'center',
        weight   = 'bold')
    plt.axis('off')
    plt.savefig(remote_path)
    plt.close('all')
# ----------------------
@app.command()
def wp_translator(
    wp   : str = typer.Option(..., '--wp', '-w', help='Working point, e.g. 300')) -> None:
    '''
    This will print the signal probability (i.e. MVA working point) given a string
    '''
    val = MVAConf.str_to_wp(value = wp)
    print (val)
# ----------------------
@app.command()
def prefit_postfit(
    update : bool = typer.Option(False, '--update', '-u', help='Will remake all plots')) -> None:
    '''
    Makes prefit and postfit plots of fit parameters
    '''
    plot_prefit_postfit(update = update)
# ----------------------
if __name__ == '__main__':
    app()

