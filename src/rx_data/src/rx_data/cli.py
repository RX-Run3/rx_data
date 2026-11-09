'''
This is the entry point for all the scripts in this project
Eventually all the non-library functionality should be accessed
through this place
'''
import os
import tqdm
import typer

from ROOT        import EnableImplicitMT
from typing      import Final
from pathlib     import Path
from dmu         import LogLevels, LogStore
from dmu.generic import Mode

from rx_common  import Project
from rx_common  import Cuts
from rx_common  import Trigger
from rx_common  import Component

from rx_data    import DBMaker, DBMakerConf
from rx_data    import SampleSplitter
from rx_data    import SamplesPrinter
from rx_data    import PFNDownloader
from rx_data    import PFNDownloaderConf
from rx_data    import SampleOrganizer
from rx_data    import FilePatcher
from post_ap    import ProductionConf
from post_ap    import PFNReaderConf, Production
from post_ap    import PFNReader, Samples

app = typer.Typer(
    help            = __doc__,
    context_settings= {"help_option_names": ["-h", "--help"]})
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

    rdr = PFNReader(
        cfg     = cfg,
        storage = _STORAGE)

    sam = rdr.get_samples(
        nickname   = nickname,
        production = production)

    if level == LogLevels.debug:
        print(sam)

    return sam
# ----------------------
@app.command()
def make_database(
    log_level : LogLevels = typer.Option(LogLevels.info, '--log_level', '-l', help = 'Logging level'),
    max_size  : int       = typer.Option(-1            , '--max_size' , '-m', help = 'Used to limit number of entries in test runs'),
    component : Component = typer.Option(...           , '--component', '-c', help = 'Sample to make database for'),
    trigger   : Trigger   = typer.Option(...           , '--trigger'  , '-t', help = 'HLT2 trigger'),
    dropped   : list[Cuts]= typer.Option(...           , '--dropped'  , '-d', help = 'List of cuts to drop with respect to full selection')) -> None:
    '''
    Used to slim ROOT files
    '''
    LogStore.set_level('rx_data:sample_emulator', log_level)
    LogStore.set_level('rx_data:db_maker'       , log_level)

    cfg = DBMakerConf(
        component    = component,
        trigger      = trigger,
        ncores       = 1,
        cuts         = {Cuts.cmb : 'mva_cmb > 0.1'},
        max_size     = max_size,
        dropped_cuts = dropped)

    mkr = DBMaker(cfg = cfg)
    mkr.run(mode = Mode.write)
# ----------------------
@app.command()
def show_samples_by_block(
    ncores  : int     = typer.Option(1  , '--ncores' , '-n'),
    project : Project = typer.Option(..., '--project', '-p')) -> None: # noqa: B008
    '''
    This will print a table with the samples available for each block
    '''
    if ncores > 1:
        log.info(f'Using {ncores} cores')
        EnableImplicitMT(ncores)

    printer = SamplesPrinter(project=project)
    printer.print_by_block()
# ----------------------
@app.command()
def download_ntuples(
    level   : LogLevels = typer.Option(LogLevels.info, '--level'  , '-l', help='Logging level'),
    nthread : int       = typer.Option(           ..., '--nthread', '-n', help='Threads to download with'),
    dry_run : bool      = typer.Option(False         , '--dry_run', '-d', help='If used will do everything but download'),
    version : str       = typer.Option(           ..., '--version', '-v', help='AP version, e.v. v1r6146')) -> None:
    '''
    Downloads ntuples from grid, before using do:

    # Make sure you have access to APD metadata
    apd-login

    # Make sure you have access to grid data
    lhcb-proxy-init -v 100:00
    '''
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
    version : str       = typer.Option(           ..., '--version', '-v', help = 'Version of analysis production, e.g. v1r5849')) -> None:
    '''
    Used to organize ntuples from AP

    These ntuples are already in local server.
    It expects ROOT files in {ANADIR}/downloaded/{version}.
    The files will be post processed by:

    - Splitting them into analyses, e.g. rk, rkstar
    - Merging them such that each job corresponds to one ROOT file
    - Renaming them
    '''

    LogStore.set_level('rx_data:sample_organizer', level)

    samples = _get_samples(version = version, level = level)
    org     = SampleOrganizer(
        cleanup = True,
        dry_run = dry_run)

    counter = 0
    for sample in tqdm.tqdm(samples, ascii = ' -', disable = level < LogLevels.info):
        if not org.organize(sample = sample):
            log.debug(f'Skipping: {sample}')
            continue

        log.debug(f'Organizing: {sample}')
        counter += 1

    nsamples = len(samples)
    log.info('-' * 30)
    log.info(f'Organized: {counter}/{nsamples}')
# ----------------------
@app.command()
def patch_files(
    dry_run : bool    = typer.Option(False, '--dry-run', '-d', help = 'Run without making changes'),
    version : str     = typer.Option(...  , '--version', '-v', help = 'Version of ntuples in main trees'),
    project : Project = typer.Option(...  , '--project', '-p', help = 'Project, e.g. rk')) -> None:
    '''
    Used to add or fix branches in main trees of specific set of ntuples
    '''
    ntup_dir = _ANADIR / 'Data' / project / f'main/{version}'
    paths    = list(ntup_dir.rglob('*.root'))
    if not paths:
        raise ValueError(f'No path found in: {ntup_dir}')

    ptc = FilePatcher(dry_run = dry_run)

    statuses : dict[int,int] = {}
    for path in tqdm.tqdm(paths, ascii = ' -'):
        status = ptc.run(path = path)

        if status not in statuses:
            statuses[status] = 1
        else:
            statuses[status]+= 1

    npatched = 0
    if 1 in statuses:
        npatched = statuses[1]

    if 2 in statuses:
        npatched = statuses[2]

    log.info(f'Patched: {npatched} files')
# ----------------------
@app.command()
def store_sample_db(
    version : str     = typer.Option(..., '--version', '-v', help = 'Version of ntuples'),
    project : Project = typer.Option(..., '--Project', '-p', help = 'E.g. rk, rkst')):
    '''
    Used to create JSON file in current directory holding list of samples and number of events
    File will be stored in `.statistics_{project}_{version}.json`
    '''
    spt = SampleSplitter(
        version = version,
        project = project)

    cache_path = _ANADIR / f'DB/statistics/{version}/{project}.json'
    spt.run(out_path = cache_path, mode = Mode.write)
# ----------------------
if __name__ == '__main__':
    app()
