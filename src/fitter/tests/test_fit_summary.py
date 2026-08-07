'''
Module with tests for FitSummary class
'''
import os
import pytest

from dmu.stats   import FitResult
from dmu         import LogStore
from fitter      import FitSummary
from typing      import Final
from pathlib     import Path

from fitter.fit_metadata import FitMetadata
from fitter.fit_summary import FitSummarizer

log=LogStore.add_logger('fitter:test_fit_summary')

_DATA_PATHS = [
    'reso_no_dtf-latest/990_800_b1/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
    'reso_no_dtf-latest/990_800_b1/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
    'reso_no_dtf-latest/990_500_b3/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
    'reso_no_dtf-latest/990_500_b3/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
]

_SIGN_PATHS = [
    'reso_no_dtf-latest/990_800_b1/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx1/brem_xx1/parameters.json',
    'reso_no_dtf-latest/990_800_b1/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx2/brem_xx2/parameters.json',
    'reso_no_dtf-latest/990_500_b3/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx1/brem_xx1/parameters.json',
    'reso_no_dtf-latest/990_500_b3/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx2/brem_xx2/parameters.json',
]

_ANADIR : Final[Path] = Path(os.environ['ANADIR'])
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('fitter:fit_summary', 10)
# ----------------------
@pytest.mark.parametrize('value', _DATA_PATHS + _SIGN_PATHS)
def test_simple(value : str) -> None:
    '''
    Test where overriden path
    '''
    path = _ANADIR / f'fits/data/{value}' 

    meta = FitMetadata.from_pars_path(path = path)
    fres = FitResult.from_json(path = path)

    data = [(meta , fres)]
    smr  = FitSummary(root = data)

    assert len(smr.root) > 0
# ----------------------
@pytest.mark.parametrize('name', ['reso_dtf-latest', 'reso_no_dtf-latest'])
def test_summarizer(name : str) -> None:
    smr = FitSummarizer(name = name, kind = 'reso')
    smr.get_summary()
# ----------------------
