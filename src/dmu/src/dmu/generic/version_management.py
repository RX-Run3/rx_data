'''
Module containing functions used to find latest, next version, etc of a path.
'''

import os
import re
import glob

from pathlib import Path
from typing  import Literal, overload
from dmu     import LogStore

log=LogStore.add_logger('dmu:version_management')
#---------------------------------------
class NoVersions(Exception):
    '''
    Needed when no versioned directory was found
    '''
#---------------------------------------
def _get_numeric_version(version : str) -> tuple[int,int]|None:
    r'''
    Parameters
    -------------
    version: Version name, e.g v1.0, v3, v7p3.

    Returns
    -------------
    Tuple with major and minor version, e.g. (1,0), (3,0) (7,3)

    Raises
    -------------
    If ANY file or directory that does not follow the regex is found
    which is not among: README.md, comparison, ignored.
    '''
    if version in ['README.md', 'comparison', 'ignored', 'latest']:
        return None

    version = version.replace('p', '.')
    mtch    =re.match(r'^v(\d+)(\.\d+)?$', version)
    if not mtch:
        raise ValueError(f'Cannot extract numeric version from: {version}')

    major, minor= mtch.groups()
    major = int(major)

    if minor is None:
        return major, 0

    minor = minor.replace('.', '')
    minor = int(minor)

    return major, minor
#---------------------------------------
@overload
def get_last_version(dir_path: str | Path, version_only: Literal[True ]) ->  str:...
@overload
def get_last_version(dir_path: str | Path, version_only: Literal[False]) -> Path:...
def get_last_version(dir_path: str | Path, version_only: bool = True) -> str | Path:
    r'''
    Parameters
    ---------------------
    dir_path: Path to directory where versioned subdirectories exist
              Anything matching `\d+`, e.g. v7, v1.2, v3p2.
              It will make these into tuples like (7,0), (1,2) and (3,2)
              and compare them
    version_only : Controls type of returned string, see below

    Returns
    ---------------------
    Either:
        - Latest version, e.g v7, v1.2, v3p2, if version_only is True (default)
        - Path to latest version, e.g. /path/to/latest/version/v7
    '''
    if isinstance(dir_path, str):
        dir_path = Path(dir_path)

    l_path = list(dir_path.glob('*'))

    if not l_path:
        raise NoVersions(f'Nothing found in {dir_path}')

    d_dir_num : dict[tuple[int,int],Path] = {}
    for path in l_path:
        value = _get_numeric_version(version=path.name)
        log.debug(f'Found version {value} from {path}')
        if value is None:
            continue

        if value in d_dir_num:
            raise ValueError(f'Found version for {path.name} which collides with existing version')

        d_dir_num[value] = path

    c_dir = sorted(d_dir_num.items())
    if not c_dir:
        raise NoVersions(f'Cannot find path in: {dir_path}')

    _, path = c_dir[-1]
    if not version_only:
        return path

    return path.name
#---------------------------------------
def get_latest_file(dir_path : str, wc : str) -> str:
    '''Will find latest file in a given directory

    Parameters
    --------------------
    dir_path (str): Directory where files are found
    wc (str): Wildcard associated to files, e.g. file_*.txt

    Returns
    --------------------
    Path to latest file, according to version
    '''
    l_path = glob.glob(f'{dir_path}/{wc}')
    if len(l_path) == 0:
        log.error(f'Cannot find files in: {dir_path}/{wc}')
        raise ValueError

    l_path.sort()

    return l_path[-1]
#---------------------------------------
def get_next_version(version : str) -> str:
    '''Pick up string symbolizing version and return next version
    Parameters
    -------------------------
    version (str) : Of the form vx.y or vx where x and y are integers. It can also be a full path

    Returns
    -------------------------
    String equal to the argument, but with the main version augmented by 1, e.g. vx+1.y

    Examples:
    -------------------------

    get_next_version('v1.1') = 'v2.1'
    get_next_version('v1'  ) = 'v2'
    '''
    if '/' in version:
        path    = version
        dirname = os.path.dirname(path)
        version = os.path.basename(path)
    else:
        dirname = None

    rgx = r'v(\d+)(\.\d+)?'

    mtch = re.match(rgx, version)
    if not mtch:
        log.error(f'Cannot match {version} with {rgx}')
        raise ValueError

    ver_org = mtch.group(1)
    ver_nxt = int(ver_org) + 1
    ver_nxt = str(ver_nxt)

    version = version.replace(f'v{ver_org}', f'v{ver_nxt}')

    if dirname is not None:
        version = f'{dirname}/{version}'

    return version
#---------------------------------------
