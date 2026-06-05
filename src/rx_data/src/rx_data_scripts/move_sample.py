'''
Script used to move samples from one project to another

Usage:

move_sample -r "^data_24.*" -s rk -t rk_no_refit

will:

- Look for all the files (friend and main trees) matching the regex "^data_24.*" in the `rk` project
- Create the `rk_no_refit` project and move each file there, with the same directory structure
'''
import os
import re
import shutil
import textwrap
import argparse

from pathlib      import Path
from dmu          import LogStore
from pydantic     import BaseModel, model_validator
from ap_utilities import decay_utilities

log=LogStore.add_logger('rx_data:move_sample')
# ----------------------
class Conf(BaseModel):
    '''
    Data class meant to contain configuration
    '''
    regex   : str
    etype   : int | None = None
    source  : str
    target  : str
    dry     : bool 
    # --------------------------------------
    @model_validator(mode = 'before')
    @classmethod
    def validate_fields(cls, data):
        '''
        Validates fields
        '''
        regex = data.get('regex')
        if regex:
            return data 

        if data['etype'] is     None:
            raise ValueError('Neither regular expression nor event type passed')

        name = decay_utilities.read_decay_name(event_type=data['etype'])
        decay= name.lower()
        regex= fr'.*{decay}.*'

        log.debug(f'Using regex: {regex}')

        data['regex'] = regex

        return data 
# ----------------------
def _get_conf() -> Conf:
    '''
    Returns config instance from arguments passed by user
    '''
    if not isinstance(__doc__, str):
        raise ValueError('Missing documentation for module')

    parser = argparse.ArgumentParser(
        prog           = 'move_sample',
        formatter_class= argparse.RawDescriptionHelpFormatter,
        description    = textwrap.dedent(__doc__).strip())

    parser.add_argument('-r', '--regex'  , type=str, help='Regular expression to match files to be moved', required=False)
    parser.add_argument('-e', '--etype'  , type=int, help='Event type of sample to move, 0 for data'     , required=False)
    parser.add_argument('-s', '--source' , type=str, help='Name of project to move files from, e.g. rk'  , required=True)
    parser.add_argument('-t', '--target' , type=str, help='Name of target project'                       , required=True)
    parser.add_argument('-l', '--loglvl' , type=int, help='Logging level'                                , default=20) 
    parser.add_argument('-d', '--dry'    , action='store_true', help='If used, will do a dry run, e.g. not move files')
    args = parser.parse_args()

    LogStore.set_level('rx_data:move_sample', args.loglvl)

    return Conf(
        regex = args.regex,
        etype = args.etype,
        dry   = args.dry,
        source= args.source,
        target= args.target)
# ----------------------
def _get_paths(cfg : Conf) -> tuple[list[Path], list[Path]]:
    '''
    Parameters
    -------------
    cfg: Config specified by user

    Returns
    -------------
    Tuple with:

    - List of paths to ROOT files
    - List of paths to directories
    '''
    ana_dir  = Path(os.environ['ANADIR'])
    root_dir = ana_dir / f'Data/{cfg.source}'
    l_fpath  = list(root_dir.rglob('*.root'))
    pattern  = re.compile(cfg.regex)
    l_fpath  = [ fpath for fpath in l_fpath if pattern.search(fpath.name)]

    l_dpath  = [ dpath for dpath in root_dir.rglob('*') if dpath.is_dir() ]

    if not l_fpath:
        log.info(f'No dataset found for: {cfg.regex}')
        return [], []

    nfile = len(l_fpath)
    ndirs = len(l_dpath)

    log.info(f'Found {nfile} files and {ndirs} directories for: {cfg.regex}')

    return l_fpath, l_dpath
# ----------------------
def _setup_dirs(
    dirs   : list[Path], 
    source : str,
    target : str) -> None:
    '''
    Parameters
    -------------
    dirs  : List of directories in directory structure
    source: Name of source project, e.g. rk
    target: Name of target project, e.g. rk_old
    '''
    cannot_make = False
    invalid_name= False

    for dir in dirs:
        str_dir = str(dir)
        nsource = str_dir.count(f'/{source}/')
        if nsource != 1:
            log.error(f'Not found one and only one occurence of {source} in {str_dir}')
            invalid_name = True
            continue

        str_dir = str_dir.replace(f'/{source}/', f'/{target}/')

        try:
            Path(str_dir).mkdir(parents=True, exist_ok=True)
        except Exception:
            log.error(f'Cannot make: {str_dir}')
            cannot_make = True

    if cannot_make or invalid_name:
        raise ValueError('Directory checks failed')
# ----------------------
def _move_files(
    files  : list[Path], 
    dry    : bool,
    source : str,
    target : str) -> None:
    '''
    Parameters
    -------------
    files : List of paths to ROOT files
    dry   : If true, will do a dry run
    source: Project which is the source of the files, e.g. rk
    target: Project to which the source file will be moved, e.g. rk_old
    '''
    for sfile in files:
        str_sfile  = str(sfile)
        str_target = str_sfile.replace(f'/{source}/', f'/{target}/')
        tfile      = Path(str_target)

        log.debug('')
        log.debug(sfile)
        log.debug('--->')
        log.debug(tfile)
        log.debug('')
        if not dry:
            tfile.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(sfile, tfile)
# ----------------------
def main():
    '''
    Entry point
    '''
    cfg                = _get_conf()
    l_fpath, l_dirpath = _get_paths(cfg=cfg)

    _setup_dirs(dirs = l_dirpath, source = cfg.source, target = cfg.target)
    _move_files(files=l_fpath, source = cfg.source, target = cfg.target, dry = cfg.dry)
# ----------------------
if __name__ == '__main__':
    main()
