'''
Script used to move samples from one project to another

Usage:

move_sample -i "^data_24.*" -s rk -t rk_no_refit

will:

- Look for all the files (friend and main trees) matching the regex "^data_24.*" in the `rk` project
- Create the `rk_no_refit` project and move each file there, with the same directory structure

This can be used also with event types:

move_sample -i 12345678 -s rk -t rk_no_refit

to target a given sample or with `for_analysis` to target all the samples:

move_sample -i for_analysis -s rk -t rk_analysis
'''
import os
import re
import shutil
import textwrap
import argparse

from dmu          import LogStore
from typing       import Final
from pathlib      import Path
from pydantic     import BaseModel, model_validator
from rx_common    import Project
from ap_utilities import decay_utilities
from rx_data      import UsedSamples

log=LogStore.add_logger('rx_data:move_sample')

_ANALYSIS_ID : Final[str] = 'for_analysis'
# ----------------------
class Conf(BaseModel):
    '''
    Data class meant to contain configuration
    '''
    identifier: str
    source    : str
    target    : str
    dry       : bool
    # --------------------------------------
    @model_validator(mode = 'before')
    @classmethod
    def validate_fields(cls, data):
        '''
        Validates fields
        '''
        identifier = data.get('identifier')

        if   re.match(r'\d{8}', identifier):
            name   = decay_utilities.read_decay_name(event_type=identifier)
            decay  = name.lower()
            regex  = fr'.*{decay}.*'
        elif identifier == _ANALYSIS_ID:
            source = data['source']
            project= Project(source)
            regex  = cls._get_analysis_regex(project = project)
        else:
            regex = identifier

        data['identifier'] = regex

        log.info(f'Using regex: {regex}')

        return data
    # --------------------------------------
    @classmethod
    def _get_analysis_regex(cls, project : Project) -> str:
        '''
        Parameters
        ---------------
        project: rk or rkstar, needed to pick config with list of samples used by analysis

        Returns
        ---------------
        Regular expression that any analysis sample should match
        '''
        obj = UsedSamples.from_project(project = project)
        ids = [ f'.*{elm}.*' for elm in obj.identifiers ]
        val = '|'.join(ids)

        return val
    # --------------------------------------
    def pick_path(self, path : Path) -> bool:
        '''
        Parameters
        --------------
        path: Path to ROOT file

        Returns
        --------------
        True if path satisfies regex
        '''
        if not path.name.endswith('.root'):
            raise ValueError(f'Not a ROOT file: {path}')

        pattern = re.compile(self.identifier)
        value   = bool(pattern.search(path.name))

        return value
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

    parser.add_argument('-i', '--identifier', type=str, help=f'Event type, regex or "{_ANALYSIS_ID}", needed to find files', required=True)
    parser.add_argument('-s', '--source'    , type=str, help='Name of project to move files from, e.g. rk'  , required=True)
    parser.add_argument('-t', '--target'    , type=str, help='Name of target project'                       , required=True)
    parser.add_argument('-l', '--loglvl'    , type=int, help='Logging level'                                , default=20)
    parser.add_argument('-d', '--dry'       , action='store_true', help='If used, will do a dry run, e.g. not move files')
    args = parser.parse_args()

    LogStore.set_level('rx_data:move_sample', args.loglvl)

    return Conf(
        identifier = args.identifier,
        dry        = args.dry,
        source     = args.source,
        target     = args.target)
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
    root_dir = ana_dir / 'Data' / cfg.source
    l_fpath  = list(root_dir.rglob('*.root'))
    l_fpath  = [ fpath for fpath in l_fpath if cfg.pick_path(path = fpath) ]
    l_dpath  = [ dpath for dpath in root_dir.rglob('*') if dpath.is_dir() ]

    if not l_fpath:
        log.warning(f'No dataset found for: {cfg.identifier}')
        return [], []

    nfile = len(l_fpath)
    ndirs = len(l_dpath)

    log.info(f'Found {nfile} files and {ndirs} directories')
    for dpath in sorted(l_dpath):
        log.info(dpath)

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
