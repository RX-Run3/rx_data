'''
Entry point for post_ap utilities
'''
import os
import typer

from pathlib     import Path
from dmu         import LogStore
from dmu.generic import utilities as gut
from post_ap     import PFNReaderConf
from post_ap     import PFNReader
from post_ap     import Production

app = typer.Typer(help=__doc__)
log = LogStore.add_logger('post_ap:cli')
# ----------------------
@app.command()
def make_info(
    group   : str = typer.Option(..., '--group'  , '-g', help = 'Nickname associated to samples, e.g. data_ecal'),
    project : str = typer.Option(..., '--project', '-p', help = 'Project name, needed to find config, e.g. rx')):
    '''
    Used to create info.yaml, needed for AnalysisProduction jobs that filter
    ntuples made by DaVinci
    '''
    data = gut.load_data(
        package = 'post_ap_data', 
        fpath   = f'filter/{project}.yaml')

    storage = Path(os.environ['ANADIR']) / 'downloads'
    cfg     = PFNReaderConf(**data)
    rdr     = PFNReader(cfg = cfg, storage = storage)
    samples = rdr.get_samples(
        production=Production.rx_2024, 
        nickname  =group)

    lines : list[str] = [ sample.info for sample in samples ]

    text = '\n'.join(lines)
    text = text.replace('PROJECT', project)

    with open(f'{group}.yaml', 'w') as ofile:
        ofile.write(text)
# ----------------------
if __name__ == '__main__':
    app()
