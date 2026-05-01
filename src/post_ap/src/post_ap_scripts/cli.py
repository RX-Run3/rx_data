'''
'''

import typer

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
    sample  : str = typer.Option(..., '--sample' , '-s'),
    version : str = typer.Option(..., '--version', '-v'),
    project : str = typer.Option(..., '--project', '-p')):

    data = gut.load_data(
        package = 'post_ap_data', 
        fpath   = f'post_ap/{project}/{version}.yaml')
    cfg     = PFNReaderConf(**data)
    rdr     = PFNReader(cfg = cfg)
    samples = rdr.get_samples(
        production=Production.rx_2024, 
        nickname  =sample)

    lines : list[str] = [ sample.info for sample in samples ]

    text = '\n'.join(lines)

    with open(f'{sample}.yaml', 'w') as ofile:
        ofile.write(text)
# ----------------------
if __name__ == '__main__':
    app()
