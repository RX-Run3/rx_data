'''
Script with tests for FCopy class
'''

import pytest

from pathlib     import Path
from dmu         import FCopy
from dmu         import LogStore
from dmu.fsystem import Server

log=LogStore.add_logger('dmu:test_fcopy')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('dmu:fsystem:fcopy', 10)
# ----------------------
def _make_paths(
    dir_path  : Path, 
    make_file : bool,
    number    : int,
    size      : int = 1) -> list[Path]:
    '''
    Parameters
    -------------
    dir      : Path to directory
    make_file: If true, will make an empty file
    number   : Number of paths to make
    size     : Size in MB, default 1

    Returns
    -------------
    List of paths
    '''
    dir_path.mkdir(parents=True, exist_ok=True)

    l_path = []
    for index in range(number):
        path = dir_path / f'{index:03}'

        if make_file:
            with open(path, 'wb') as f:
                f.seek(size * 1024 * 1024 - 1)
                f.write(b'\0')

        l_path.append(path)

    return l_path
# ----------------------
def test_local(tmp_path : Path) -> None:
    '''
    Simplest test
    '''
    l_source = _make_paths(dir_path=tmp_path / 'source', make_file= True, number=10)
    l_target = _make_paths(dir_path=tmp_path / 'target', make_file=False, number=10)

    fcp = FCopy(server=Server.local.host)
    for source, target in zip(l_source, l_target, strict = True):
        fcp.copy(source=source, target=target)
# ----------------------
