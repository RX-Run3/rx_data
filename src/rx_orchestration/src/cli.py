'''
This is the entry point for utilities needed by orchestration code
'''

import typer

from pathlib               import Path
from dmu.logging.log_store import LogStore
from dmu.generic           import utilities as gut

app = typer.Typer(
    help            = __doc__,
    context_settings= {"help_option_names": ["-h", "--help"]})
log = LogStore.add_logger('rx_orchestration:cli')
# ----------------------
@app.command()
def dump_logs(
    path      : Path = typer.Option('logs.json',      '--path', '-p', help='Path to JSON file with logs'),
    substring : str  = typer.Option(        ..., '--substring', '-s', help='Substring in log section')) -> None:
    '''
    Will create a log file per job containing given substring
    '''
    if not path.exists():
        raise FileNotFoundError(f'File not found: {path}')

    log.info(f'Searching for: {substring} in {path}')

    data = gut.load_json(path = path)
    logs = data['job_logs']

    out_dir = Path(f'./logs/{substring}')
    out_dir.mkdir(parents=True, exist_ok=True)

    for job_name, job_data in logs.items():
        string = job_data['logs']

        if substring not in string:
            continue

        log.info(f'String found in: {job_name}')

        out_path = out_dir / f'{job_name}.log'
        with open(out_path, 'w', encoding='utf-8') as ofile:
            ofile.write(string)
# ----------------------
@app.command()
def dummy():
    pass
# ----------------------
if __name__ == '__main__':
    app()
