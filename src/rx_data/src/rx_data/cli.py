'''
This is the entry point for all the scripts in this project
Eventually all the non-library functionality should be accessed
through this place
'''
import os
import tqdm
import typer

from typing     import Final
from pathlib    import Path
from dmu        import LogLevels, LogStore
from rx_common  import Project 
from rx_data    import SamplesPrinter
from rx_data    import PFNDownloader
from rx_data    import PFNDownloaderConf
from rx_data    import SampleOrganizer
from rx_data    import FilePatcher
from post_ap    import ProductionConf
from post_ap    import PFNReaderConf, Production
from post_ap    import PFNReader, Samples

app = typer.Typer(help=__doc__)
log = LogStore.add_logger('rx_data:cli')
_ANADIR  : Final[Path] = Path(os.environ['ANADIR'])
_STORAGE : Final[Path] = Path(f'{_ANADIR}/downloaded')
# ----------------------
def _get_samples(version : str, level : LogLevels) -> Samples:
    '''
    Parameters
    --------------
    version: Version of input files
    level  : Logging level

    Returns
    --------------
    Object representing samples to download from AP
    '''
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
        chunks    = 8,
        chunksize = 16_000_000,
        version   = version,
        out_dir   = _STORAGE,
        dry_run   = dry_run,
        nthread   = nthread)

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
    dry_run : bool      = typer.Option(False         , '--dry-run', '-d', help = 'If used, will do dry run', is_flag = True),
    level   : LogLevels = typer.Option(LogLevels.info, '--level'  , '-l', help = 'Logging level'),
    nproc   : int       = typer.Option(             4, '--nproc'  , '-n', help = 'Number of processes to run in parallel over samples'),
    version : str       = typer.Option(           ..., '--version', '-v', help = 'Version of analysis production, e.g. v1r5849')) -> None:

    LogStore.set_level('rx_data:sample_organizer', level)

    samples = _get_samples(version = version, level = level)
    org = SampleOrganizer(
        cleanup = True,
        dry_run = dry_run,
        storage = _STORAGE)

    for sample in tqdm.tqdm(samples, ascii = ' -'):
        org.organize(sample = sample)
# ----------------------
@app.command()
def patch_files(
    version : str     = typer.Option(..., '--version', '-v'),
    project : Project = typer.Option(..., '--project', '-p')) -> None:

    ptc = FilePatcher(
        version = version,
        project = project)
    ptc.run()
# ----------------------
if __name__ == '__main__':
    app()
