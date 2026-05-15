'''
Script used to copy ntuples from mounted filesystem
'''
import os
import argparse
import multiprocessing

import tqdm
import numpy
import ap_utilities.decays.utilities as aput

from pathlib                        import Path
from omegaconf                      import DictConfig
from dmu.generic.version_management import get_last_version
from dmu.logging.log_store          import LogStore
from dmu.generic                    import utilities as gut
from dmu                            import FCopy
from rx_data                        import utilities as ut

log = LogStore.add_logger('rx_data:copy_samples')
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
    conf    : DictConfig 
    d_data  : dict
    host    : str
    l_source: list[Path]
    timeout : int
    serv    : str

    skipped_friend : str|None
    fcp            : FCopy
    out_dir        : Path # Path to ana_dir/{kind}/{version}
    pfs_dir = Path(os.environ['PFS_ANADIR']) / 'Data'
    ana_dir = Path(os.environ['ANADIR'    ]) / 'Data'
    vers    = None
    l_kind  = [
        'all',
        'main',
        'mva',
        'hop',
        'mass',
        'smear',
        'swp_jpsi_misid',
        'swp_cascade',
        'brem_track_2']
    copied_files : int   = 0
    copied_size  : float = 0
# -----------------------------------------
def _parse_args():
    parser = argparse.ArgumentParser(description='Script used to copy files from remote server to laptop')
    parser.add_argument('-k', '--kind', type=      str, help='Type of files', choices=Data.l_kind, required=True)
    parser.add_argument('-p', '--proj', type=      str, help='Name of YAML config file, e.g. rk', required=True, choices=['rk', 'rkst', 'rk_nopid', 'rkst_nopid'])
    parser.add_argument('-s', '--skip', type=      str, help='Friend tree to skip', choices=Data.l_kind)
    parser.add_argument('-l', '--logl', type=      int, help='Logger level', choices=[5, 10, 20, 30], default=20)
    parser.add_argument('-n', '--nprc', type=      int, help='Number of process to download with, with zero, will download all files at once', default=1)
    parser.add_argument('-t', '--tout', type=      int, help='Timeout, used to check if server is reachable', default = 10)
    parser.add_argument('-S', '--serv', type=      str, help='Sever number, e.g. 001', default = '')
    parser.add_argument('-v', '--vers', type=      str, help='Version of files, only makes sense if kind is not "all"')
    parser.add_argument('-H', '--host', type=      str, help='Server from which files will be transferred', choices = ['IHEP', 'LOCAL'], default = 'IHEP')
    parser.add_argument('-d', '--dry' ,           help='If used, will do not copy files', action='store_true')
    args = parser.parse_args()

    Data.serv = args.serv
    Data.kind = args.kind
    Data.proj = args.proj
    Data.conf = gut.load_conf(package='rx_data_data', fpath=f'copy_files/{args.proj}.yaml')
    Data.vers = args.vers
    Data.dry  = args.dry
    Data.nprc = args.nprc
    Data.timeout        = args.tout
    Data.skipped_friend = args.skip
    Data.host           = _get_host(args.host)

    LogStore.set_level('rx_data:copy_samples', args.logl)
# ----------------------
def _get_host(name : str) -> str:
    '''
    Parameters
    -------------
    name: Nickname for host

    Returns
    -------------
    Actual host name
    '''
    match name:
        case 'IHEP':
            return f'campoverde@lxlogin{Data.serv}.ihep.ac.cn'
        case 'LOCAL':
            return ''
        case _:
            raise ValueError(f'Invalid host: {name}')
# -----------------------------------------
def _is_right_trigger(path : Path) -> bool:
    l_trigger  = Data.conf.triggers
    _, trigger = ut.info_from_path(path)

    flag = str(trigger) in l_trigger

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
    d_samp   = Data.conf.samples
    l_source = []
    log.info(90 * '-')
    log.info(f'{"Sample":<50}{"Identifier":<25}{"Paths":<10}{"Size [MB]":<20}')
    log.info(90 * '-')
    for l_identifier in d_samp.values():
        for identifier in l_identifier:
            id_str        = str(identifier)
            l_source_samp = [ source for source in Data.l_source if id_str in source.name and _is_right_trigger(source) ]

            npath     = len(l_source_samp)
            size      = _get_total_size(l_path=l_source_samp)
            if not id_str.startswith('data'):
                nickname = aput.read_decay_name(event_type=id_str)
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
def _get_version(kind : str) -> str:
    '''
    Get latest or user defined version for given kind of friend trees 
    '''
    if Data.vers is not None:
        return Data.vers

    knd_dir = Data.pfs_dir / Data.proj / kind
    if not knd_dir.exists():
        raise ValueError(f'Cannot find {knd_dir}, likely PFS was not mounted')

    vers    = get_last_version(dir_path = knd_dir, version_only=True)

    log.debug(f'Latest version {vers} found in {knd_dir}')

    return vers
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
    vers    = _get_version(kind)
    inp_dir = Data.pfs_dir / f'{Data.proj}/{kind}/{vers}'
    l_path  = list(inp_dir.glob('*.root'))

    Data.out_dir = Data.ana_dir / f'{Data.proj}/{kind}/{vers}'
    Data.out_dir.mkdir(parents=True, exist_ok=True)

    log.info(f'Source: {inp_dir}')
    log.info(f'Target: {Data.out_dir}')

    nsource = len(l_path)
    if nsource == 0:
        raise ValueError(f'No files found in: {inp_dir}')

    log.info(f'Found {nsource} files')

    Data.l_source = l_path
# ----------------------
def _copy_sample(source : Path) -> int:
    '''
    Parameters
    ---------------
    source: Path to file to be copied

    Returns
    ---------------
    Number of files that were actually copied
    '''
    target= Data.out_dir/source.name

    if not hasattr(Data, 'fcp'):
        Data.fcp = FCopy(
            source  = Data.host, 
            timeout = Data.timeout)

    Data.copied_files += 1
    Data.copied_size  += source.stat().st_size / 1_000_000_000
    log.debug('')
    log.debug(source)
    log.debug('--->')
    log.debug(target)
    log.debug('')

    if not Data.dry:
        Data.fcp.copy(source=source, target=target)

    return 1
# -----------------------------------------
def _download_group(group : list[Path]) -> int:
    nfiles = len(group)
    log.debug(f'Downloading {nfiles} files in parallel')

    if nfiles == 1:
        log.warning('Found group of one file, not using multiprocessing')
        ncopied = _copy_sample(source=group[0])
        return ncopied

    with multiprocessing.Pool() as pool:
        log.debug(f'Will run {nfiles} processes')
        l_ncopied = pool.map(_copy_sample, group)
        ncopied   = sum(l_ncopied)

    return ncopied
# -----------------------------------------
def _group_paths(l_path : list[Path]) -> list[list[Path]]:
    '''
    Parameters
    --------------------
    l_path: List of paths of files to download

    Returns
    --------------------
    Group of lists of files to download. Each group will be downloaded separately
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

    log.debug('Found the following groups:')
    for group in l_l_path:
        nfiles = len(group)
        log.debug(f'   {nfiles}')

    return l_l_path
# -----------------------------------------
def _download_kind(kind : str) -> None:
    '''
    Parameters
    -------------------
    kind: E.g. mva, mass, brem_track_2
    '''

    log.info(f'Copying files for kind {kind}')
    _initialize(kind = kind)

    l_path = _get_source_paths()
    l_group= _group_paths(l_path)
    ncopied= 0
    for group in tqdm.tqdm(l_group, ascii=' -'):
        ncopied += _download_group(group)

    log.info(f'Copied {ncopied} files for kind {kind}')
# -----------------------------------------
def main():
    '''
    Starts here
    '''
    _parse_args()

    if Data.kind == 'all':
        l_kind = Data.l_kind
    else:
        l_kind = [Data.kind]

    for kind in l_kind:
        if kind == 'all':
            continue

        if kind == Data.skipped_friend:
            continue

        _download_kind(kind = kind)

    log.info(f'Copied {Data.copied_files} ({Data.copied_size:.2f} Gb) files in total')
# -----------------------------------------
if __name__ == '__main__':
    main()
