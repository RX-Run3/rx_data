'''
Module with tests for PFNSplitter class
'''
import json
import pytest

from typing                import Final
from pathlib               import Path
from importlib.resources   import files
from functools             import cache
from dmu                   import LogStore
from dmu.generic           import version_management as vmn
from rx_data               import PathSplitter

# TODO: Add rkst_nopid project
_PROJECTS : Final[list[str]] = ['rx', 'nopid']

log   = LogStore.add_logger('')
log   = LogStore.add_logger('rx_data:test_path_splitter')
# ----------------------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_data:path_splitter', 10)
# ----------------------------------------
@cache
def _get_pfns(analysis : str) -> list[Path]:
    lfn_dir= files('rx_data_lfns').joinpath(analysis)
    lfn_dir= Path(str(lfn_dir))
    lfn_ver= vmn.get_last_version(dir_path=lfn_dir, version_only=False)
    l_path = list(lfn_ver.glob(pattern='*.json'))
    if not l_path:
        raise ValueError(f'No JSON path found in {lfn_ver}')

    l_pfn  = []
    for path in l_path:
        with open(path, encoding='utf-8') as ifile:
            l_pfn += json.load(ifile)

    return l_pfn
# ----------------------------------------
@pytest.mark.parametrize('analysis', _PROJECTS)
def test_default(analysis : str, tmp_path : Path):
    '''
    Default usage
    '''
    pfns  = _get_pfns(analysis=analysis)
    spl   = PathSplitter(paths = pfns)
    data  = spl.split(nested=False)

    string = data.model_dump_json(indent = 2)
    path   = tmp_path / f'default_{analysis}.json'
    path.write_text(string)
# ----------------------------------------
@pytest.mark.parametrize('analysis', _PROJECTS)
def test_nested(analysis : str, tmp_path : Path):
    '''
    Dumps it with nesting sample:trigger:list of files
    '''
    l_pfn = _get_pfns(analysis=analysis)
    spl   = PathSplitter(paths = l_pfn)
    data  = spl.split(nested=True)

    string = data.model_dump_json(indent = 2)
    path   = tmp_path / f'nested_{analysis}.json'
    path.write_text(string)
# ----------------------------------------
@pytest.mark.parametrize('analysis', _PROJECTS)
def test_max_files(analysis : str, tmp_path : Path):
    '''
    Will only read 100 files
    '''
    l_pfn = _get_pfns(analysis=analysis)
    spl   = PathSplitter(paths = l_pfn, max_files=100)
    data  = spl.split(nested=False)

    string = data.model_dump_json(indent = 2)
    path   = tmp_path / f'max_files_{analysis}.json'
    path.write_text(string)
# ----------------------------------------
@pytest.mark.parametrize('analysis', _PROJECTS)
@pytest.mark.parametrize('naming'  , ['new', 'old'])
def test_sample_naming(
    naming   : str, 
    tmp_path : Path,
    analysis : str):
    '''
    Will only read 100 files
    '''
    l_pfn = _get_pfns(analysis=analysis)
    spl   = PathSplitter(paths = l_pfn, sample_naming=naming)
    data  = spl.split(nested=False)

    string = data.model_dump_json(indent = 2)
    path   = tmp_path / f'naming_{analysis}.json'
    path.write_text(string)
# ----------------------------------------
