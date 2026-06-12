'''
Script used to copy ntuples from mounted filesystem
'''
import argparse
import multiprocessing
import tqdm
import numpy

from typing       import Final
from functools    import partial
from ap_utilities import decay_utilities
from pathlib      import Path
from dmu.fsystem  import Server
from dmu          import LogStore
from dmu          import FCopy
from rx_data      import utilities as ut
from rx_data      import UsedSamples

log = LogStore.add_logger('rx_data:copy_samples')

_FRIENDS : Final[list[str]] = [
    'all',
    'main',
    'mva',
    'hop',
    'mass',
    'smear',
    'swp_jpsi_misid',
    'swp_cascade',
    'brem_track_2']
# -----------------------------------------
class Data:
    '''
    Class holding attributes meant to be shared

    Attributes:
    -------------------
    l_source: 
    '''
    kind    : str
    proj    : str
    dry     : bool
    nprc    : int
    conf    : UsedSamples 
    d_data  : dict
    server  : Server 
    l_source: list[Path]
    timeout : int

    skipped_friend : str|None
    vers    : str 
    copied_files : int   = 0
    copied_size  : float = 0
# -----------------------------------------
def _parse_args():
    parser = argparse.ArgumentParser(description='Script used to copy files from remote server to laptop')
    parser.add_argument('-k', '--kind', type=    str, help='Type of files', choices=_FRIENDS, required=True)
    parser.add_argument('-p', '--proj', type=    str, help='Name of YAML config file, e.g. rk', required=True, choices=['rk', 'rkst', 'rk_nopid', 'rkst_nopid'])
    parser.add_argument('-s', '--skip', type=    str, help='Friend tree to skip', choices=_FRIENDS)
    parser.add_argument('-l', '--logl', type=    int, help='Logger level', choices=[5, 10, 20, 30], default=20)
    parser.add_argument('-n', '--nprc', type=    int, help='Number of process to transfer with, with zero will transfer all files at once', default=1)
    parser.add_argument('-t', '--tout', type=    int, help='Timeout, used to check if server is reachable', default = 10)
    parser.add_argument('-v', '--vers', type=    str, help='Version of files, only makes sense if kind is not "all"', required = True)
    parser.add_argument('-S', '--serv', type= Server, help='Server to which files will be transferred', choices = list(Server))
    parser.add_argument('-d', '--dry' ,               help='If used, will do not copy files', action='store_true')
    args = parser.parse_args()

    conf = UsedSamples.from_project(project = args.proj)

    Data.kind           = args.kind
    Data.proj           = args.proj
    Data.conf           = conf
    Data.vers           = args.vers
    Data.dry            = args.dry
    Data.nprc           = args.nprc
    Data.timeout        = args.tout
    Data.skipped_friend = args.skip
    Data.server         = args.serv

    LogStore.set_level('rx_data:copy_samples', args.logl)
    LogStore.set_level('dmu:fsystem:fcopy'   , args.logl)
# -----------------------------------------
def _is_right_trigger(path : Path) -> bool:
    l_trigger  = Data.conf.triggers
    _, trigger = ut.info_from_path(path)

    flag = trigger in l_trigger

    return flag
# -----------------------------------------
def _get_total_size(l_path : list[Path]) -> int:
    '''
    Parameters
    -------------
    l_path: List of paths to ROOT files

    Returns
    -------------
    Size in MB
    '''
    l_size = [ path.stat().st_size / (1024 * 1024) for path in l_path ]
    fsize  = sum(l_size)

    return int(fsize)
# -----------------------------------------
def _get_source_paths() -> list[Path]:
    l_source = []
    log.info(90 * '-')
    log.info(f'{"Sample":<50}{"Identifier":<25}{"Paths":<10}{"Size [MB]":<20}')
    log.info(90 * '-')
    for l_identifier in Data.conf.samples.values():
        for identifier in l_identifier:
            id_str        = str(identifier).lower()
            l_source_samp = [ source for source in Data.l_source if id_str in source.name and _is_right_trigger(source) ]

            npath     = len(l_source_samp)
            size      = _get_total_size(l_path=l_source_samp)
            if not id_str.startswith('data'):
                nickname = decay_utilities.read_decay_name(event_type=id_str)
            else:
                nickname = 'data' 

            log.info(f'{nickname:<50}{id_str:<25}{npath:<10}{size:<20}')
            l_source += l_source_samp

    log.info(90 * '-')

    nsource = len(l_source)
    if nsource == 0:
        raise ValueError('No files found')

    log.info(f'Found {nsource} files in source path')
    for source in l_source:
        log.verbose(source)

    return l_source
# -----------------------------------------
def _initialize(kind : str):
    '''
    This function will initialize:
    - Data.out_dir : Full path to output directory 
    - Data.l_source: List of paths with inputs to copy

    Parameters
    ---------------
    kind: Kind of friend tree, e.g. main
    '''
    if Data.vers is not None and Data.kind == 'all':
        raise ValueError(f'Specified version {Data.vers} for kind {Data.kind}')

    log.info(f'Initializing for trees of type: {kind}')
    inp_dir = Server.local.data_dir / Data.proj / kind / Data.vers

    log.info(f'Searching for files in: {Server.local.host}:{inp_dir}')
    l_path  = list(inp_dir.glob(pattern = '*.root'))
    if not l_path:
        raise ValueError('No paths found')

    log.info(f'Source: {inp_dir}')
    log.info(f'Target: {Data.server.data_dir}')

    nsource = len(l_path)
    if nsource == 0:
        raise ValueError(f'No files found in: {inp_dir}')

    log.info(f'Found {nsource} files')

    Data.l_source = l_path
# ----------------------
def _copy_sample(
    fcp    : FCopy,
    source : Path) -> int:
    '''
    Parameters
    ---------------
    fcp   : File copier instance
    source: Path to file to be copied

    Returns
    ---------------
    Number of files that were actually copied
    '''
    target = Data.server.data_dir / Data.proj / Data.kind / Data.vers / source.name

    Data.copied_files += 1
    Data.copied_size  += source.stat().st_size / 1_000_000_000
    log.debug('')
    log.debug(source)
    log.debug('--->')
    log.debug(target)
    log.debug('')

    if not Data.dry:
        fcp.copy(source=source, target=target)

    return 1
# -----------------------------------------
def _transfer_group(group : list[Path], fcp : FCopy) -> int:
    nfiles = len(group)
    log.debug(f'Transferring {nfiles} files in parallel')

    if nfiles == 1:
        ncopied = _copy_sample(
            fcp   = fcp,
            source= group[0])
        return ncopied

    with multiprocessing.Pool() as pool:
        log.debug(f'Will run {nfiles} processes')
        fn = partial(_copy_sample, fcp) 
        l_ncopied = pool.map(fn, group)
        ncopied   = sum(l_ncopied)

    return ncopied
# -----------------------------------------
def _group_paths(l_path : list[Path]) -> list[list[Path]]:
    '''
    Parameters
    --------------------
    l_path: List of paths of files to transfer 

    Returns
    --------------------
    Group of lists of files to transfer. Each group will be transferred separately
    '''
    if Data.nprc <  0:
        raise ValueError(f'Number of processes has to be larger or equal to 1, found: {Data.nprc}')

    if Data.nprc == 0:
        return [ l_path ]

    if Data.nprc == 1:
        l_group = [ [path] for path in l_path ]
        return l_group

    arr_path   = numpy.array(l_path, dtype=object)

    if len(arr_path) < Data.nprc:
        return [ [ Path(obj) for obj in arr_path ] ]

    ngroups    = len(arr_path) // Data.nprc
    l_arr_path = numpy.array_split(arr_path, ngroups)
    l_l_path   = [ [ Path(obj) for obj in arr_path ] for arr_path in l_arr_path ]

    groups : dict[int,int] = dict()
    for group in l_l_path:
        nfiles = len(group)
        if nfiles not in groups:
            groups[nfiles] = 1
        else:
            groups[nfiles]+= 1

    log.info('')
    log.info('Found the following groups:')
    log.info('')
    for size, freq in groups.items():
        log.info(f'{size:<20}{freq:<20}')

    return l_l_path
# -----------------------------------------
def _transfer_kind(kind : str, fcp : FCopy) -> None:
    '''
    Parameters
    -------------------
    kind: E.g. mva, mass, brem_track_2
    '''
    log.info(f'Copying files for kind {kind}')
    _initialize(kind = kind)

    l_path  = _get_source_paths()
    l_group = _group_paths(l_path)
    ncopied = 0

    for group in tqdm.tqdm(l_group, ascii=' -'):
        ncopied  += _transfer_group(
            group = group, 
            fcp   = fcp)

    log.info(f'Copied {ncopied} files for kind {kind}')
# -----------------------------------------
def main():
    '''
    Entry point for sample copier
    '''
    _parse_args()
    fcp = FCopy(server = Data.server.host)
    if Data.kind == 'all':
        l_kind = _FRIENDS 
    else:
        l_kind = [Data.kind]

    for kind in l_kind:
        if kind == 'all':
            continue

        if kind == Data.skipped_friend:
            continue

        log.info(f'Transferring from host: {Data.server}')
        _transfer_kind(kind = kind, fcp = fcp)

    log.info(f'Copied {Data.copied_files} ({Data.copied_size:.2f} Gb) files in total')
# -----------------------------------------
if __name__ == '__main__':
    main()
