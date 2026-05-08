'''
This is the entry point for all the scripts in this project
Eventually all the non-library functionality should be accessed
through this place
'''

import typer

from dmu        import LogLevels, LogStore
from rx_common  import Project 
from rx_data    import SamplesPrinter
from post_ap    import ProductionConf
from post_ap    import PFNReaderConf, Production
from post_ap    import PFNReader

app = typer.Typer(help=__doc__)
log = LogStore.add_logger('rx_data:cli')
# ----------------------
@app.command()
def show_samples_by_block(project : Project = typer.Option(..., '--project', '-p')) -> None:
    '''
    This will print a table with the samples available for each block
    '''
    printer = SamplesPrinter(project=project)
    printer.print_by_block()
# ----------------------
@app.command()
def download_ntuples(
    level   : int = typer.Option(LogLevels.info, '--level'  , '-l'),
    version : str = typer.Option(           ..., '--version', '-v')) -> None:

    LogStore.set_level('post_ap:pfn_reader', level)

    nickname   = 'all'
    production = Production.rx_filter

    cfg_prod = ProductionConf(
        versions = {nickname : version},
        samples  = {nickname :    None},
        fractions= {nickname :    None},
    )

    productions = {production : cfg_prod}

    cfg = PFNReaderConf(
        working_group = 'RD',
        productions   = productions)

    rdr = PFNReader(cfg = cfg)
    sam = rdr.get_samples(
        nickname   = nickname, 
        production = production)

    _   = sam
# ----------------------
if __name__ == '__main__':
    app()
