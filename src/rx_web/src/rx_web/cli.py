'''
This script is meant to be the entry point for all the functionalities
provided by this project
'''

import os
import typer
import subprocess

from pathlib               import Path
from dmu.logging.log_store import LogStore

app    = typer.Typer(help=__doc__)
log    = LogStore.add_logger('rx_web:cli')
ANADIR = Path(os.environ['ANADIR'])
# ----------------------
@app.command()
def dummy():
    pass
# ----------------------
@app.command()
def collect_plots(
    name : str = typer.Option(..., '--name', '-n', help='Name of fits, e.g. rare'))-> None:
    '''
    This will collect in a tarball the directory structure with plots of fits 
    '''
    fit_dir  = ANADIR / 'fits/data' / name

    log.info(f'Picking files from: {fit_dir}')

    find_cmd = ['find', '-L', fit_dir, '-path', '*/.*', '-prune', '-o', '-name', '*.png', '-print0']
    tar_cmd  = ['tar', '--null', '-h', '-czf', 'images.tar.gz', '-T', '-']

    find_proc = subprocess.Popen(find_cmd, stdout=subprocess.PIPE)
    tar_proc  = subprocess.Popen( tar_cmd, stdin=find_proc.stdout)

    stdout = find_proc.stdout
    if stdout is None:
        raise ValueError('Cannot find STDOUT from find step')

    stdout.close()  # let find_proc receive SIGPIPE if tar exits early
    tar_proc.communicate()
# ----------------------
@app.command()
def make_html(
    ncpu    : str = typer.Option(      '4', '--ncpu'   , '-n', help='Number of CPUs to use'),
    browser : str = typer.Option('firefox', '--browser', '-b', help='Name of browser to open website')) -> None:
    '''
    Creates website from path to plots and opens site
    '''
    create_cmd = ['sigal', 'build', '-n', ncpu, '-c', 'src/rx_web/sigal.conf.py', f'{ANADIR}/plots/web', f'{ANADIR}/www']
    server_cmd = ['sigal', 'serve', f'{ANADIR}/www']

    subprocess.Popen(create_cmd)
    subprocess.Popen(server_cmd)
    subprocess.Popen(['firefox', 'http://127.0.0.1:8000/'])
# ----------------------
if __name__ == '__main__':
    app()

