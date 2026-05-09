'''
This is the entry point for all the scripts in this project
Eventually all the non-library functionality should be accessed
through this place
'''

import typer

from typing     import Final
from pathlib    import Path
from dmu        import LogLevels, LogStore
from rx_common  import Project 
from rx_data    import SamplesPrinter
from rx_data    import PFNDownloader
from rx_data    import PFNDownloaderConf
from post_ap    import ProductionConf
from post_ap    import PFNReaderConf, Production
from post_ap    import PFNReader, Samples

app = typer.Typer(help=__doc__)
log = LogStore.add_logger('rx_data:cli')
_STORAGE : Final[Path] = Path('/home/acampove/external_02/Data/downloaded')
# ----------------------
def _get_samples(version : str, level : LogLevels) -> Samples:
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

    if level == LogLevels.debug:
        print(sam)

    return sam
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
    level   : LogLevels = typer.Option(LogLevels.info, '--level'  , '-l'),
    nthread : int       = typer.Option(           ..., '--nthread', '-n'),
    dry_run : bool      = typer.Option(False         , '--dry_run', '-d'),
    version : str       = typer.Option(           ..., '--version', '-v')) -> None:

    LogStore.set_level('post_ap:pfn_reader', level)

    cfg = PFNDownloaderConf(
        version = version,
        out_dir = _STORAGE,
        dry_run = dry_run,
        nthread = nthread)

    sam = _get_samples(
        level   = level,
        version = version)

    dwn = PFNDownloader(
        cfg     = cfg,
        samples = sam)
    dwn.run()
# ----------------------
@app.command()
def organize_paths(
    level   : LogLevels = typer.Option(LogLevels.info, '--level'  , '-l'),
    version : str       = typer.Option(           ..., '--version', '-v')) -> None:

    samples = _get_samples(version = version, level = level)
    org = SampleOrganizer(storage = _STORAGE)
    for sample in samples:
        org.organize(sample = sample)
# ----------------------
if __name__ == '__main__':
    app()
