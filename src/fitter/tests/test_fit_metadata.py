'''
Module with tests for FitMetadata class
'''
import os
import pytest

from typing    import Final 
from pathlib   import Path
from fitter    import FitMetadata
from dmu       import LogStore

_DATA_PATHS = [
    'reso_no_dtf-latest/990_800_b1/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
    'reso_no_dtf-latest/990_800_b1/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
    'reso_no_dtf-latest/990_800_b3/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
    'reso_no_dtf-latest/990_800_b3/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
]

_SIGN_PATHS = [
    'reso_no_dtf-latest/990_800_b1/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx1/brem_xx1/parameters.json',
    'reso_no_dtf-latest/990_800_b1/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx2/brem_xx2/parameters.json',
    'reso_no_dtf-latest/990_500_b3/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx1/brem_xx1/parameters.json',
    'reso_no_dtf-latest/990_500_b3/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx2/brem_xx2/parameters.json',
]

_ANADIR : Final[Path] = Path(os.environ['ANADIR'])

log=LogStore.add_logger('rx_fitter:test_fit_metadata')
# --------------------------------------------------
@pytest.mark.parametrize('path', _DATA_PATHS + _SIGN_PATHS)
def test_from_data_path(path : Path):
    path = _ANADIR / f'fits/data/{path}' 

    meta = FitMetadata.from_pars_path(path = path)

    log.info(meta)
    log.info(meta.as_str)
# --------------------------------------------------
def test_equivalence():
    root   = _ANADIR / 'fits/data' 
    paths  = [ root / path for path in _DATA_PATHS ]

    meta_0 = FitMetadata.from_pars_path(path = paths[0])
    meta_1 = FitMetadata.from_pars_path(path = paths[1])
    meta_2 = FitMetadata.from_pars_path(path = paths[2])
    meta_3 = FitMetadata.from_pars_path(path = paths[3])

    assert not meta_0.is_equivalent(other = meta_1, exclude = 'block') # different brems
    assert     meta_1.is_equivalent(other = meta_1, exclude = 'block') # same object
    assert     meta_0.is_equivalent(other = meta_2, exclude = 'block') # different blocks
    assert     meta_1.is_equivalent(other = meta_3, exclude = 'block') # different blocks
# --------------------------------------------------
