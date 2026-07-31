'''
Module with tests for FitSummary class
'''
import pytest

from dmu     import LogStore
from fitter  import FitSummary, FitOutput
from pathlib import Path

log=LogStore.add_logger('fitter:test_fit_summary')

_PATHS : list[Path] = [
    Path('/home/acampove/RX/fits/data/reso_dtf-latest/990_800_b1/reso/rkst/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_x12/parameters.json'),
    Path('/home/acampove/RX/fits/data/reso_dtf-latest/990_800_b1/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_x12/parameters.json'),
]
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('fitter:fit_summary', 10)
# ----------------------
@pytest.mark.parametrize('path', _PATHS)
def test_fit_output(path : Path):
    fou  = FitOutput(path = path)

    print(fou)
# ----------------------
@pytest.mark.parametrize('name', ['reso_dtf-latest'])
def test_local(name : str) -> None:
    '''
    Test where overriden path
    '''
    smr = FitSummary(name = name)
    df  = smr.get_df(force_update = True)

    assert len(df) > 0

    print('')
    print(df)
    for column in df.columns:
        print(column)
# ----------------------
@pytest.mark.parametrize('force_update', [True, False])
def test_update(force_update : bool) -> None:
    '''
    Test updating the parquet file
    '''
    smr = FitSummary(name = 'reso_no_dtf')
    df  = smr.get_df(force_update = force_update)

    assert len(df) > 0

    print('')
    print(df)
# ----------------------
