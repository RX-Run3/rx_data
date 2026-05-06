'''
Module with tests for FitSummary class 
'''
import pytest

from dmu       import LogStore
from fitter    import FitSummary
from pathlib   import Path
from rx_common import Component

log=LogStore.add_logger('fitter:test_fit_summary')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('fitter:fit_summary', 10)
# ----------------------
@pytest.mark.parametrize('name', ['reso_no_dtf'])
def test_simple(name : str) -> None:
    '''
    Simplest test
    '''
    smr = FitSummary(name = name, signal = Component.bpkpjpsiee)
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
    smr = FitSummary(name='reso_no_dtf', signal = Component.bpkpjpsiee)
    df  = smr.get_df(force_update = force_update)

    assert len(df) > 0

    print('')
    print(df)
# ----------------------
@pytest.mark.parametrize('name'  , ['conv_none', 'photon_veto_v1'])
@pytest.mark.parametrize('signal', [Component.bpkpee])
def test_with_signal(
    name     : str,
    signal   : Component,
    tmp_path : Path) -> None:
    '''
    Test picking up only data parameters, for e.g. combinatorial studies
    '''
    smr = FitSummary(name=name, signal = signal)
    df  = smr.get_df(force_update = True)

    assert len(df) > 0

    df.T.to_markdown(buf = tmp_path / f'{name}.md')
# ----------------------
@pytest.mark.parametrize('name'  , ['conv_none', 'photon_veto_v1'])
def test_no_signal(
    name     : str,
    tmp_path : Path) -> None:
    '''
    Test picking up only data parameters, for e.g. combinatorial studies
    '''
    smr = FitSummary(name=name, signal = None)
    df  = smr.get_df(force_update = True)

    assert len(df) > 0

    df.T.to_markdown(buf = tmp_path / f'{name}.md')
# ----------------------
