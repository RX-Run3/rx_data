'''
Module with tests for FitMetadata class
'''
import os
import pytest

from typing    import Final 
from pathlib   import Path
from fitter    import FitMetadata

_DATA_PATHS = [
    'reso_no_dtf/990_800_b1/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
    'reso_no_dtf/990_800_b1/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
    'reso_no_dtf/990_500_b3/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
    'reso_no_dtf/990_500_b3/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
]

_SIGN_PATHS = [
    'reso_no_dtf/990_800_b1/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx1/brem_xx1/parameters.json',
    'reso_no_dtf/990_800_b1/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx2/brem_xx2/parameters.json',
    'reso_no_dtf/990_500_b3/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx1/brem_xx1/parameters.json',
    'reso_no_dtf/990_500_b3/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx2/brem_xx2/parameters.json',
]

_ANADIR : Final[Path] = Path(os.environ['ANADIR'])
# --------------------------------------------------
@pytest.mark.parametrize('path', _DATA_PATHS + _SIGN_PATHS)
def test_from_data_path(path : Path):
    path = _ANADIR / f'fits/data/{path}' 

    FitMetadata.from_pars_path(path = path)
# --------------------------------------------------
